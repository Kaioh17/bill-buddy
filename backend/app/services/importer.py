"""importAccount: pull new bank transactions from Plaid into the database.

One import is one database transaction. Everything Plaid sent is applied, the cursor
is saved last, and a single commit makes it all real. Any failure rolls the lot back,
so old data and the old cursor stay as they were and the next run retries the same
changes.
Shared by the exchange route, "sync now" and the webhook.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_token
from app.core import clock
from app.core.exception import (
    AppException,
    ReconnectRequiredError,
    SyncFailedError,
    SyncInProgressError,
)
from app.core.plaid import PlaidClient, PlaidError
from app.models.linked_accounts import LinkedAccount, LinkStatus
from app.models.transactions import Transaction
from app.services import detection

logger = logging.getLogger(__name__)

LOCK_TIMEOUT = timedelta(minutes=10)  # a lock older than this is a crashed import
SYNC_INTERVAL = timedelta(hours=24)  # next scheduled sync after a good one
RETRY_DELAYS = (timedelta(minutes=15), timedelta(hours=1), timedelta(hours=4))
RETRY_EXHAUSTED_DELAY = timedelta(hours=24)  # after 3 retries, still keep trying daily
HISTORY_COMPLETE = "HISTORICAL_UPDATE_COMPLETE"


@dataclass
class ImportResult:
    added: int = 0
    modified: int = 0
    removed: int = 0


async def import_account(
    db: AsyncSession, plaid: PlaidClient, account: LinkedAccount
) -> ImportResult:
    """Raises SyncInProgressError, SyncFailedError or ReconnectRequiredError. By the
    time one is raised the failure is already recorded on the account."""
    now = clock.now()
    await _acquire_lock(db, account, now)
    try:
        token = decrypt_token(account.access_token_enc)
        added, modified, removed, cursor, status = await _fetch(
            plaid, token, account.cursor
        )
        result = await _apply(db, account, added, modified, removed, now)

        account.cursor = cursor  # last, so a failure above can never skip changes
        account.last_sync_at = now
        account.next_sync = now + SYNC_INTERVAL
        account.last_error = None
        account.sync_failures = 0
        account.status = LinkStatus.ACTIVE
        account.history_ready = account.history_ready or status == HISTORY_COMPLETE
        account.sync_locked_at = None
        await db.commit()
    except Exception as exc:
        await db.rollback()
        await db.refresh(account)
        raise await _record_failure(db, account, exc, now) from exc

    await _detect(db, account)
    logger.info(
        "import_ok",
        extra={
            "user_id": str(account.user_id),
            "account_id": str(account.id),
            "added": result.added,
            "modified": result.modified,
            "removed": result.removed,
        },
    )
    return result


async def _detect(db: AsyncSession, account: LinkedAccount) -> None:
    """Find subscriptions in the fresh data. The import is already committed, so a bug
    here is logged and never fails the sync."""
    try:
        await detection.detect_subscriptions(db, account.user_id)
    except Exception:
        await db.rollback()
        logger.exception(
            "detection_failed",
            extra={"user_id": str(account.user_id), "account_id": str(account.id)},
        )


async def _acquire_lock(db: AsyncSession, account: LinkedAccount, now) -> None:
    """One import per account at a time. One UPDATE, so two requests can't both win."""
    taken = await db.execute(
        update(LinkedAccount)
        .where(
            LinkedAccount.id == account.id,
            or_(
                LinkedAccount.sync_locked_at.is_(None),
                LinkedAccount.sync_locked_at < now - LOCK_TIMEOUT,
            ),
        )
        .values(sync_locked_at=now)
        .execution_options(synchronize_session=False)
    )
    if taken.rowcount != 1:
        await db.rollback()
        raise SyncInProgressError()
    await db.commit()
    await db.refresh(account)


async def _fetch(plaid: PlaidClient, token: str, cursor: str | None):
    # ponytail: all pages are held in memory before applying. Fine for one person's
    # accounts, batch the apply step if a single import ever reaches many thousands.
    added, modified, removed = [], [], []
    while True:
        data = await plaid.transactions_sync(token, cursor)
        added += data["added"]
        modified += data["modified"]
        removed += [r["transaction_id"] for r in data["removed"]]
        cursor = data["next_cursor"]
        if not data["has_more"]:
            return (
                added,
                modified,
                removed,
                cursor,
                data.get("transactions_update_status"),
            )


async def _apply(
    db: AsyncSession, account, added, modified, removed, now
) -> ImportResult:
    cutoff = _twelve_months_ago(now.date())
    result = ImportResult()

    def eligible(t: dict) -> bool:
        return not t["pending"] and date.fromisoformat(t["date"]) >= cutoff

    wanted = {t["transaction_id"]: t for t in added if eligible(t)}
    # ponytail: one IN query, fine below the database's bind-parameter limit (~30k).
    have = set(
        await db.scalars(
            select(Transaction.transaction_id).where(
                Transaction.transaction_id.in_(wanted)
            )
        )
    )
    for tid, t in wanted.items():
        if tid not in have:
            db.add(
                Transaction(
                    transaction_id=tid,
                    linked_account_id=account.id,
                    user_id=account.user_id,
                    **_columns(t),
                )
            )
            result.added += 1

    for t in modified:
        if not eligible(t):
            continue
        row = await db.get(Transaction, t["transaction_id"])
        if row and row.linked_account_id == account.id:
            for name, value in _columns(t).items():
                setattr(row, name, value)
            result.modified += 1

    if removed:
        gone = await db.execute(
            delete(Transaction).where(
                Transaction.transaction_id.in_(removed),
                Transaction.linked_account_id == account.id,  # never another account's
            )
        )
        result.removed = gone.rowcount
    return result


def _columns(t: dict) -> dict:
    category = t.get("personal_finance_category") or {}
    authorized = t.get("authorized_date")
    return {
        "plaid_account_id": t["account_id"],
        "amount": Decimal(str(t["amount"])),
        "iso_currency_code": t.get("iso_currency_code"),
        "date": date.fromisoformat(t["date"]),
        "authorized_date": date.fromisoformat(authorized) if authorized else None,
        "pending": t["pending"],
        "merchant_name": t.get("merchant_name"),
        "merchant_entity_id": t.get("merchant_entity_id"),
        "original_description": t.get("original_description"),
        "pfc_primary": category.get("primary"),
        "pfc_detailed": category.get("detailed"),
    }


def _twelve_months_ago(today: date) -> date:
    try:
        return today.replace(year=today.year - 1)
    except ValueError:  # 29 Feb
        return today.replace(year=today.year - 1, day=28)


async def _record_failure(
    db: AsyncSession, account: LinkedAccount, exc: Exception, now
) -> AppException:
    """Save why the import failed and when to retry. Returns the error to raise."""
    if isinstance(exc, PlaidError):
        code, permanent = exc.code, exc.permanent
    else:
        code, permanent = "IMPORT_ERROR", False
        logger.exception("import_crashed", extra={"account_id": str(account.id)})

    account.sync_locked_at = None
    account.last_error = code
    if permanent:
        # Retrying can't help, the user must reconnect. Nothing is scheduled.
        account.status = LinkStatus.NEEDS
        account.next_sync = None
        error: AppException = ReconnectRequiredError()
    else:
        account.sync_failures = (account.sync_failures or 0) + 1
        retries = len(RETRY_DELAYS)
        if account.sync_failures <= retries:
            delay = RETRY_DELAYS[account.sync_failures - 1]
        else:
            delay = RETRY_EXHAUSTED_DELAY
            # TODO(notifications): tell the user their data may be stale.
            logger.warning(
                "sync_retries_exhausted", extra={"account_id": str(account.id)}
            )
        account.next_sync = now + delay
        error = SyncFailedError()
    await db.commit()
    logger.warning(
        "sync_failed",
        extra={
            "user_id": str(account.user_id),
            "account_id": str(account.id),
            "error": code,
            "permanent": permanent,
        },
    )
    return error
