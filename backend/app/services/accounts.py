"""Linked bank accounts: list, sync now, disconnect. Queries are scoped to the user."""

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_token
from app.core.exception import BankProviderError, NotFoundError, ReconnectRequiredError
from app.core.plaid import PlaidClient, PlaidError
from app.models.linked_accounts import LinkedAccount, LinkStatus
from app.models.transactions import Transaction
from app.schema.accounts import SyncOut
from app.services.importer import import_account

logger = logging.getLogger(__name__)

# Plaid no longer knows this item, so there is nothing left to revoke.
ALREADY_GONE = {"ITEM_NOT_FOUND", "INVALID_ACCESS_TOKEN"}


async def list_accounts(db: AsyncSession, user_id: uuid.UUID) -> list[LinkedAccount]:
    rows = await db.scalars(
        select(LinkedAccount)
        .where(
            LinkedAccount.user_id == user_id,
            LinkedAccount.status != LinkStatus.DISCONNECTED,
        )
        .order_by(LinkedAccount.created_at)
    )
    return list(rows)


async def get_owned(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID
) -> LinkedAccount:
    """Someone else's account looks exactly like one that does not exist."""
    account = await db.scalar(
        select(LinkedAccount).where(
            LinkedAccount.id == account_id,
            LinkedAccount.user_id == user_id,
            LinkedAccount.status != LinkStatus.DISCONNECTED,
        )
    )
    if account is None:
        raise NotFoundError("Account not found")
    return account


async def sync_now(
    db: AsyncSession, plaid: PlaidClient, user_id: uuid.UUID, account_id: uuid.UUID
) -> SyncOut:
    account = await get_owned(db, user_id, account_id)
    if account.status == LinkStatus.NEEDS:
        raise ReconnectRequiredError()
    result = await import_account(db, plaid, account)
    return SyncOut(
        last_sync_at=account.last_sync_at,
        added=result.added,
        modified=result.modified,
        removed=result.removed,
    )


async def disconnect(
    db: AsyncSession,
    plaid: PlaidClient,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    delete_transactions: bool,
) -> None:
    """Revoke the Plaid token first. If that fails the account stays connected, so
    the user is never told it is disconnected while the bank access is still live."""
    account = await get_owned(db, user_id, account_id)
    try:
        await plaid.item_remove(decrypt_token(account.access_token_enc))
    except PlaidError as exc:
        if exc.code not in ALREADY_GONE:
            raise BankProviderError() from None

    account.status = LinkStatus.DISCONNECTED
    account.access_token_enc = b""  # useless once revoked, no reason to keep it
    account.next_sync = None
    if delete_transactions:
        await db.execute(
            delete(Transaction).where(Transaction.linked_account_id == account.id)
        )
    await db.commit()
    logger.info(
        "account_disconnected",
        extra={
            "user_id": str(user_id),
            "account_id": str(account.id),
            "transactions_deleted": delete_transactions,
        },
    )
