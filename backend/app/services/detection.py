"""detectSubscriptions (FR 2a): turn a user's bank transactions into subscriptions.

For each merchant and frequency, find the longest run of charges whose gaps fit the
frequency, then score it: ACTUAL when every rule holds, LIKELY when exactly one is
unmet (the user confirms or dismisses it), nothing when two or more are.
Runs after each import for WEEKLY and MONTHLY. YEARLY is supported here but not run
yet: it needs 24 months of history and only 12 are stored (the yearly job is open).

Safe to run again and again. A subscription is keyed by (merchant, frequency), new
charges are saved as matched payments once, a dismissed detection is never suggested
again, and a subscription the user confirmed is never demoted back to LIKELY.
Manual subscriptions are never read or written here.
"""

import calendar
import logging
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.models.matched_payments import MatchedPayment
from app.models.subscriptions import (
    DismissedSubscription,
    Frequency,
    Subscription,
    SubscriptionSource,
    SubscriptionStatus,
)
from app.models.transactions import Transaction
from app.services.catalog import all_entries, find_entry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rule:
    min_charges: int
    gap: tuple[int, int]  # days between two charges for them to count as one series
    drift: int  # most the gaps may differ from each other before dates are "uneven"
    grace: int  # days past the expected date before a subscription counts as stopped


# Tune the rules here, nowhere else (Design Report: kept in configuration).
RULES = {
    Frequency.WEEKLY: Rule(min_charges=3, gap=(5, 9), drift=2, grace=14),
    Frequency.MONTHLY: Rule(min_charges=3, gap=(25, 36), drift=5, grace=15),
    Frequency.YEARLY: Rule(min_charges=2, gap=(350, 380), drift=10, grace=30),
}
AMOUNT_TOLERANCE = Decimal("0.05")  # more than 5% between charges is a changed amount
ACTUAL_MIN_CHARGES = 3
EXCLUDED_CATEGORIES = {"TRANSFER_IN", "TRANSFER_OUT", "INCOME", "BANK_FEES"}

TOO_FEW = "too few payments"
AMOUNT_CHANGED = "amount changed, maybe a plan change"
UNEVEN = "payment dates uneven"


async def detect_subscriptions(
    db: AsyncSession,
    user_id: uuid.UUID,
    frequencies: tuple[Frequency, ...] = (Frequency.WEEKLY, Frequency.MONTHLY),
) -> None:
    today = clock.now().date()
    charges = await _eligible_charges(db, user_id)
    entries = await all_entries(db)
    dismissed = {
        (d.merchant_key, d.frequency)
        for d in await db.scalars(
            select(DismissedSubscription).where(
                DismissedSubscription.user_id == user_id
            )
        )
    }
    rows = {
        (s.merchant_key, s.frequency): s
        for s in await db.scalars(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.source == SubscriptionSource.DETECTED,
            )
        )
    }
    matched = set(
        await db.scalars(
            select(MatchedPayment.transaction_id).where(
                MatchedPayment.user_id == user_id
            )
        )
    )

    for key, merchant in _by_merchant(charges).items():
        for frequency in frequencies:
            rule = RULES[frequency]
            series = _longest_series(merchant, rule)
            if len(series) < rule.min_charges:
                continue
            status, reasons = _score(series, rule)
            if status is None or (key, frequency) in dismissed:
                continue

            last = series[-1]
            entry = find_entry(
                entries,
                last.merchant_entity_id,
                last.merchant_name,
                last.original_description,
            )
            sub = rows.get((key, frequency))
            if sub is None:
                sub = Subscription(
                    user_id=user_id,
                    source=SubscriptionSource.DETECTED,
                    merchant_key=key,
                    frequency=frequency,
                )
                db.add(sub)
                rows[(key, frequency)] = sub
            elif sub.status == SubscriptionStatus.ACTUAL:
                status, reasons = SubscriptionStatus.ACTUAL, []  # never demote

            sub.status, sub.likely_reasons = status, reasons
            sub.name = entry.name if entry else _display_name(last)
            sub.catalog_entry_id = entry.id if entry else None
            sub.service_type = entry.service_type if entry else None
            sub.category = entry.category if entry else _plaid_category(last)
            sub.amount = last.amount
            sub.last_payment_date = last.date
            sub.next_expected_date = _next_date(last.date, frequency)

            await db.flush()  # a new subscription needs its id for the payments
            for c in series:
                if c.transaction_id not in matched:
                    matched.add(c.transaction_id)
                    db.add(
                        MatchedPayment(
                            subscription_id=sub.id,
                            user_id=user_id,
                            transaction_id=c.transaction_id,
                            date=c.date,
                            amount=c.amount,
                            merchant_name=_display_name(c),
                        )
                    )

    for (_, frequency), sub in rows.items():
        grace = timedelta(days=RULES[frequency].grace)
        sub.is_active = today <= sub.next_expected_date + grace
    await db.commit()
    logger.info(
        "detection_ok", extra={"user_id": str(user_id), "subscriptions": len(rows)}
    )


async def _eligible_charges(db: AsyncSession, user_id: uuid.UUID) -> list[Transaction]:
    """Money out, not pending, not a transfer or income. Plaid sends money out as a
    positive amount."""
    rows = await db.scalars(
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.pending.is_(False),
            Transaction.amount > 0,
        )
        .order_by(Transaction.date)
    )
    return [t for t in rows if t.pfc_primary not in EXCLUDED_CATEGORIES]


def _merchant_key(t: Transaction) -> str | None:
    if t.merchant_entity_id:
        return t.merchant_entity_id
    name = (t.merchant_name or t.original_description or "").strip().lower()
    return f"name:{name}" if name else None


def _by_merchant(charges: list[Transaction]) -> dict[str, list[Transaction]]:
    groups: dict[str, list[Transaction]] = {}
    for t in charges:  # already in date order
        if key := _merchant_key(t):
            groups.setdefault(key, []).append(t)
    return groups


def _longest_series(charges: list[Transaction], rule: Rule) -> list[Transaction]:
    """The longest run where every gap fits the frequency. The latest wins a tie."""
    # ponytail: a second charge on the same day breaks the run (gap 0). Merge same-day
    # charges first if a merchant ever double-posts.
    lo, hi = rule.gap
    best: list[Transaction] = []
    run: list[Transaction] = []
    for t in charges:
        if run and lo <= (t.date - run[-1].date).days <= hi:
            run.append(t)
        else:
            run = [t]
        if len(run) >= len(best):
            best = list(run)
    return best


def _score(series: list[Transaction], rule: Rule):
    """scoreSeries: ACTUAL, LIKELY with its reason, or (None, [])."""
    unmet = []
    if len(series) < ACTUAL_MIN_CHARGES:
        unmet.append(TOO_FEW)
    amounts = [t.amount for t in series]
    if max(amounts) - min(amounts) > AMOUNT_TOLERANCE * max(amounts):
        unmet.append(AMOUNT_CHANGED)
    gaps = [(b.date - a.date).days for a, b in zip(series, series[1:], strict=False)]
    if max(gaps) - min(gaps) > rule.drift:
        unmet.append(UNEVEN)
    if not unmet:
        return SubscriptionStatus.ACTUAL, []
    if len(unmet) == 1:
        return SubscriptionStatus.LIKELY, unmet
    return None, []


def _display_name(t: Transaction) -> str:
    return t.merchant_name or t.original_description or "Unknown merchant"


def _plaid_category(t: Transaction) -> str | None:
    return t.pfc_primary.replace("_", " ").capitalize() if t.pfc_primary else None


def _next_date(last: date, frequency: Frequency) -> date:
    if frequency == Frequency.WEEKLY:
        return last + timedelta(days=7)
    months = 12 if frequency == Frequency.YEARLY else 1
    year, month = divmod(last.month - 1 + months, 12)
    year, month = last.year + year, month + 1
    return date(year, month, min(last.day, calendar.monthrange(year, month)[1]))
