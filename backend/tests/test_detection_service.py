"""detectSubscriptions (FR 2a): which charge series become subscriptions, and how they
are scored. Today is frozen at 2026-11-22 (see tests/fakes.py)."""

import datetime as dt
from decimal import Decimal

import pytest

from app.models.matched_payments import MatchedPayment
from app.models.subscriptions import (
    DismissedSubscription,
    Frequency,
    Subscription,
    SubscriptionSource,
    SubscriptionStatus,
)
from app.services.detection import detect_subscriptions
from tests.fakes import ago

pytestmark = pytest.mark.anyio

MONTHLY = ago(70, 40, 10)  # 30 day gaps, last charge 2026-11-12
DEFAULT = (Frequency.WEEKLY, Frequency.MONTHLY)
ALL = (Frequency.WEEKLY, Frequency.MONTHLY, Frequency.YEARLY)


async def detect(session, user_id, frequencies=DEFAULT):
    await detect_subscriptions(session, user_id, frequencies)


# ---- the 3 charge rule (TC-05, TC-06) ----


async def test_three_monthly_charges_are_an_actual_subscription(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", MONTHLY)

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.source == SubscriptionSource.DETECTED
    assert sub.status == SubscriptionStatus.ACTUAL
    assert sub.frequency == Frequency.MONTHLY
    assert sub.name == "Netflix"
    assert sub.amount == Decimal("15.99")
    assert sub.likely_reasons == []
    assert sub.last_payment_date == dt.date(2026, 11, 12)
    assert sub.next_expected_date == dt.date(2026, 12, 12)
    assert sub.is_active is True
    assert len(await all_rows(MatchedPayment)) == 3


async def test_two_monthly_charges_are_not_a_subscription(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", ago(40, 10))

    await detect(session, user_id)

    assert await all_rows(Subscription) == []


async def test_three_weekly_charges_are_a_weekly_subscription(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Meal Kit", ago(15, 8, 1))

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.frequency == Frequency.WEEKLY
    assert sub.status == SubscriptionStatus.ACTUAL
    assert sub.next_expected_date == dt.date(2026, 11, 28)


async def test_irregular_charges_are_not_a_subscription(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Corner Shop", ago(100, 83, 20, 3))

    await detect(session, user_id)

    assert await all_rows(Subscription) == []


async def test_merchants_are_detected_separately(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", MONTHLY)
    await add_series(acct, "Spotify", MONTHLY, amounts=[9.99] * 3)

    await detect(session, user_id)

    assert {s.name for s in await all_rows(Subscription)} == {"Netflix", "Spotify"}


# ---- scoring: one unmet rule is LIKELY, two is nothing ----


async def test_a_changed_amount_makes_it_likely(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", MONTHLY, amounts=[15.99, 15.99, 22.99])

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.status == SubscriptionStatus.LIKELY
    assert sub.likely_reasons == ["amount changed, maybe a plan change"]
    assert sub.amount == Decimal("22.99")  # the latest charge


async def test_month_length_differences_are_not_uneven_dates(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Gym", ago(73, 45, 14))  # gaps 28 and 31 days

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.status == SubscriptionStatus.ACTUAL


async def test_dates_drifting_past_the_allowance_make_it_likely(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Gym", ago(95, 66, 30))  # gaps 29 and 36 days

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.status == SubscriptionStatus.LIKELY
    assert sub.likely_reasons == ["payment dates uneven"]


async def test_two_unmet_rules_are_not_a_subscription(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Gym", ago(95, 66, 30), amounts=[10, 10, 30])

    await detect(session, user_id)

    assert await all_rows(Subscription) == []


async def test_two_yearly_charges_are_likely_and_only_when_asked_for(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Domain", ago(364, 0), amounts=[12, 12])

    await detect(session, user_id)  # weekly and monthly only
    assert await all_rows(Subscription) == []

    await detect(session, user_id, ALL)
    [sub] = await all_rows(Subscription)
    assert sub.frequency == Frequency.YEARLY
    assert sub.status == SubscriptionStatus.LIKELY
    assert sub.likely_reasons == ["too few payments"]


# ---- which charges count ----


@pytest.mark.parametrize(
    "overrides",
    [
        {"pending": True},
        {"amount": Decimal("-15.99")},  # money in
        {"pfc_primary": "TRANSFER_OUT"},
        {"pfc_primary": "INCOME"},
    ],
)
async def test_ineligible_charges_are_ignored(
    session, frozen_now, make_account, add_txn, user_id, all_rows, overrides
):
    acct = await make_account(user_id)
    for i, day in enumerate(MONTHLY):
        await add_txn(acct, f"bad-{i}", merchant_name="Bad Co", date=day, **overrides)

    await detect(session, user_id)

    assert await all_rows(Subscription) == []


async def test_one_pending_charge_leaves_too_few_to_detect(
    session, frozen_now, make_account, add_txn, user_id, all_rows
):
    acct = await make_account(user_id)
    for i, day in enumerate(MONTHLY):
        await add_txn(acct, f"n-{i}", merchant_name="Netflix", date=day, pending=i == 2)

    await detect(session, user_id)

    assert await all_rows(Subscription) == []


# ---- re-running ----


async def test_running_twice_creates_no_duplicates(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", MONTHLY)

    await detect(session, user_id)
    await detect(session, user_id)

    assert len(await all_rows(Subscription)) == 1
    assert len(await all_rows(MatchedPayment)) == 3


async def test_a_new_charge_updates_the_subscription(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", ago(100, 70, 40))
    await detect(session, user_id)

    await add_series(acct, "Netflix", ago(10))
    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.last_payment_date == dt.date(2026, 11, 12)
    assert len(await all_rows(MatchedPayment)) == 4


async def test_a_confirmed_subscription_is_never_demoted(
    session, frozen_now, make_account, add_series, make_sub, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", MONTHLY, amounts=[15.99, 15.99, 22.99])
    await make_sub(
        user_id, status=SubscriptionStatus.ACTUAL, frequency=Frequency.MONTHLY
    )

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.status == SubscriptionStatus.ACTUAL
    assert sub.likely_reasons == []
    assert sub.amount == Decimal("22.99")


async def test_a_dismissed_detection_does_not_come_back(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", MONTHLY, amounts=[15.99, 15.99, 22.99])
    session.add(
        DismissedSubscription(
            user_id=user_id, merchant_key="name:netflix", frequency=Frequency.MONTHLY
        )
    )
    await session.commit()

    await detect(session, user_id)

    assert await all_rows(Subscription) == []


async def test_a_subscription_goes_inactive_when_payments_stop(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Old Gym", ago(160, 130, 100))  # last charge 100 days ago

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.is_active is False


# ---- isolation ----


async def test_only_the_users_own_transactions_are_used(
    session, frozen_now, make_account, add_series, user_id, other_user_id, all_rows
):
    theirs = await make_account(other_user_id)
    await add_series(theirs, "Netflix", MONTHLY)

    await detect(session, user_id)

    assert await all_rows(Subscription) == []


async def test_manual_subscriptions_are_left_alone(
    session, frozen_now, make_account, add_series, make_sub, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(acct, "Netflix", MONTHLY)
    await make_sub(
        user_id,
        source=SubscriptionSource.MANUAL,
        merchant_key=None,
        status=None,
        name="Netflix (mine)",
        amount=Decimal("1.00"),
        is_active=False,
    )

    await detect(session, user_id)

    manual = [s for s in await all_rows(Subscription) if s.source == "MANUAL"]
    assert [(s.name, s.amount, s.is_active) for s in manual] == [
        ("Netflix (mine)", Decimal("1.00"), False)
    ]
    assert len(await all_rows(Subscription)) == 2


# ---- catalog matching ----


async def test_a_catalog_alias_names_and_classifies_the_subscription(
    session, frozen_now, make_account, add_series, make_entry, user_id, all_rows
):
    acct = await make_account(user_id)
    entry = await make_entry(
        "Netflix", aliases=["netflix"], service_type="Video streaming"
    )
    await add_series(acct, "NETFLIX.COM", MONTHLY)

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.name == "Netflix"
    assert sub.catalog_entry_id == entry.id
    assert sub.service_type == "Video streaming"
    assert sub.category == "Entertainment"


async def test_a_plaid_entity_id_matches_before_any_alias(
    session, frozen_now, make_account, add_series, make_entry, user_id, all_rows
):
    acct = await make_account(user_id)
    await make_entry("Wrong", aliases=["acme"])
    right = await make_entry("Right", aliases=[], merchant_entity_ids=["ent-9"])
    await add_series(acct, "Acme Streaming", MONTHLY, merchant_entity_id="ent-9")

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.catalog_entry_id == right.id


async def test_an_unmatched_merchant_keeps_its_name_and_plaid_category(
    session, frozen_now, make_account, add_series, user_id, all_rows
):
    acct = await make_account(user_id)
    await add_series(
        acct, "Local Gym", MONTHLY, pfc_primary="PERSONAL_CARE", merchant_entity_id=None
    )

    await detect(session, user_id)

    [sub] = await all_rows(Subscription)
    assert sub.name == "Local Gym"
    assert sub.catalog_entry_id is None
    assert sub.service_type is None
    assert sub.category == "Personal care"
