"""runReconciliation (FR 3): compare the assumed list with what the bank shows."""

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.models.assumed_entries import AssumedEntry
from app.models.catalog_entries import CatalogEntry
from app.models.subscriptions import (
    Subscription,
    SubscriptionSource,
    SubscriptionStatus,
)
from app.models.transactions import Transaction
from app.schema.reconciliation import ReconciliationOut, UnconfirmedOut, UnexpectedOut
from app.services.catalog import matches

CONFIRM_WINDOW = timedelta(days=60)


async def reconcile(db: AsyncSession, user_id: uuid.UUID) -> ReconciliationOut:
    entries = list(
        await db.scalars(
            select(CatalogEntry)
            .join(AssumedEntry, AssumedEntry.catalog_entry_id == CatalogEntry.id)
            .where(AssumedEntry.user_id == user_id)
            .order_by(CatalogEntry.name)
        )
    )
    assumed = {e.id for e in entries}

    actual = await db.scalars(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.source == SubscriptionSource.DETECTED,
            Subscription.status == SubscriptionStatus.ACTUAL,
            Subscription.is_active.is_(True),
        )
        .order_by(Subscription.name)
    )
    unexpected = [
        UnexpectedOut(
            subscription_id=s.id,
            name=s.name,
            last_payment_date=s.last_payment_date,
            amount=s.amount,
        )
        for s in actual
        if s.catalog_entry_id not in assumed  # also true for no catalog match at all
    ]

    # Every bank payment counts, not only detected subscriptions, so any recent
    # payment is enough to confirm a service.
    # ponytail: entries x payments in Python, fine for one person's 12 months. Move to
    # SQL if a user ever has many thousands of transactions.
    payments = list(
        await db.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.pending.is_(False),
                Transaction.amount > 0,
            )
            .order_by(Transaction.date.desc())
        )
    )
    cutoff = clock.now().date() - CONFIRM_WINDOW  # exactly 60 days ago counts as paid
    unconfirmed = []
    for entry in entries:
        last = next(
            (
                t
                for t in payments  # newest first
                if matches(
                    entry, t.merchant_entity_id, t.merchant_name, t.original_description
                )
            ),
            None,
        )
        if last is None or last.date < cutoff:
            unconfirmed.append(
                UnconfirmedOut(
                    catalog_entry_id=entry.id,
                    name=entry.name,
                    last_payment_date=last.date if last else None,
                    amount=last.amount if last else None,
                )
            )
    return ReconciliationOut(unexpected=unexpected, unconfirmed=unconfirmed)
