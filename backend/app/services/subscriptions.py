"""Subscriptions list, confirm and dismiss of LIKELY detections, scoped to the user."""

import uuid
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exception import NotFoundError, NotLikelyError
from app.models.matched_payments import MatchedPayment
from app.models.subscriptions import (
    DismissedSubscription,
    Subscription,
    SubscriptionSource,
    SubscriptionStatus,
)
from app.schema.subscriptions import SubscriptionOut
from app.services.catalog import assumed_ids


async def list_subscriptions(
    db: AsyncSession, user_id: uuid.UUID
) -> list[SubscriptionOut]:
    """Active items, LIKELY ones included, soonest payment first."""
    rows = list(
        await db.scalars(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.is_active.is_(True))
            .order_by(Subscription.next_expected_date, Subscription.name)
        )
    )
    assumed = await assumed_ids(db, user_id)

    # FR 2c: two or more ACTUAL subscriptions of one specific service type.
    groups: dict[str, list[str]] = defaultdict(list)
    for s in rows:
        if s.status == SubscriptionStatus.ACTUAL and s.service_type:
            groups[s.service_type].append(s.name)

    def similar(s: Subscription) -> list[str]:
        if s.status != SubscriptionStatus.ACTUAL or not s.service_type:
            return []
        return (
            [n for n in groups[s.service_type] if n != s.name]
            if len(groups[s.service_type]) > 1
            else []
        )

    return [
        SubscriptionOut(
            **{c: getattr(s, c) for c in _COPIED},
            label=_label(s),
            on_assumed_list=s.catalog_entry_id in assumed,
            similar_to=similar(s),
        )
        for s in rows
    ]


_COPIED = (
    "id", "name", "frequency", "kind", "category", "service_type", "amount",
    "last_payment_date", "next_expected_date", "likely_reasons",
)  # fmt: skip


def _label(s: Subscription) -> str:
    if s.source == SubscriptionSource.MANUAL:
        return "manual"
    return s.status.value.lower()


async def _get_likely(
    db: AsyncSession, user_id: uuid.UUID, sub_id: uuid.UUID
) -> Subscription:
    """Someone else's, a manual one and a missing one are all the same 404."""
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.id == sub_id,
            Subscription.user_id == user_id,
            Subscription.source == SubscriptionSource.DETECTED,
        )
    )
    if sub is None:
        raise NotFoundError("Subscription not found")
    if sub.status != SubscriptionStatus.LIKELY:
        raise NotLikelyError()
    return sub


async def confirm(db: AsyncSession, user_id: uuid.UUID, sub_id: uuid.UUID) -> None:
    sub = await _get_likely(db, user_id, sub_id)
    sub.status = SubscriptionStatus.ACTUAL
    sub.likely_reasons = []
    await db.commit()


async def dismiss(db: AsyncSession, user_id: uuid.UUID, sub_id: uuid.UUID) -> None:
    """Delete it and remember the rejection so detection never suggests it again."""
    sub = await _get_likely(db, user_id, sub_id)
    db.add(
        DismissedSubscription(
            user_id=user_id, merchant_key=sub.merchant_key, frequency=sub.frequency
        )
    )
    # Explicit, so it also works where the database does not enforce the cascade.
    await db.execute(
        delete(MatchedPayment).where(MatchedPayment.subscription_id == sub.id)
    )
    await db.delete(sub)
    await db.commit()
