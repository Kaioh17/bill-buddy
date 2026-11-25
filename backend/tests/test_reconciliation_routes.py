"""/reconciliation: unexpected and unconfirmed (FR 3, TC-09, TC-10).
Today is frozen at 2026-11-22, so 60 days ago is 2026-09-23."""

import pytest

from app.models.assumed_entries import AssumedEntry
from tests.fakes import ago

pytestmark = pytest.mark.anyio


async def assume(sessions, user_id, *entries):
    async with sessions() as s:
        for e in entries:
            s.add(AssumedEntry(user_id=user_id, catalog_entry_id=e.id))
        await s.commit()


async def report(api, auth) -> dict:
    r = await api.get("/reconciliation", headers=auth)
    assert r.status_code == 200
    return r.json()["data"]


async def test_route_needs_a_session(api):
    assert (await api.get("/reconciliation")).status_code == 401


async def test_nothing_is_reported_for_a_new_user(api, auth, frozen_now):
    assert await report(api, auth) == {"unexpected": [], "unconfirmed": []}


# ---- unexpected (TC-09) ----


async def test_an_actual_subscription_off_the_assumed_list_is_unexpected(
    api, auth, frozen_now, make_sub, make_entry, sessions, user_id
):
    spotify = await make_entry("Spotify")
    await assume(sessions, user_id, spotify)
    await make_sub(user_id, name="Hulu", merchant_key="hulu")

    data = await report(api, auth)

    [item] = data["unexpected"]
    assert item["name"] == "Hulu"
    assert item["last_payment_date"] == "2026-11-12"
    assert item["amount"] == "15.99"
    assert "subscription_id" in item


async def test_an_assumed_subscription_is_not_unexpected(
    api, auth, frozen_now, make_sub, make_entry, sessions, user_id
):
    netflix = await make_entry("Netflix")
    await assume(sessions, user_id, netflix)
    await make_sub(user_id, name="Netflix", catalog_entry_id=netflix.id)

    assert (await report(api, auth))["unexpected"] == []


async def test_likely_inactive_manual_and_other_users_rows_are_not_unexpected(
    api, auth, frozen_now, make_sub, user_id, other_user_id
):
    from app.models.subscriptions import SubscriptionSource, SubscriptionStatus

    await make_sub(user_id, merchant_key="a", status=SubscriptionStatus.LIKELY)
    await make_sub(user_id, merchant_key="b", is_active=False)
    await make_sub(
        user_id,
        source=SubscriptionSource.MANUAL,
        merchant_key=None,
        status=None,
    )
    await make_sub(other_user_id, merchant_key="c")

    assert (await report(api, auth))["unexpected"] == []


# ---- unconfirmed (TC-10) ----


@pytest.mark.parametrize(
    ("days", "unconfirmed"), [(59, False), (60, False), (61, True)]
)
async def test_unconfirmed_boundary_at_60_days(
    api,
    auth,
    frozen_now,
    make_account,
    add_series,
    make_entry,
    sessions,
    user_id,
    days,
    unconfirmed,
):
    acct = await make_account(user_id)
    netflix = await make_entry("Netflix")
    await assume(sessions, user_id, netflix)
    await add_series(acct, "Netflix", ago(days))

    data = await report(api, auth)

    assert [i["name"] for i in data["unconfirmed"]] == (
        ["Netflix"] if unconfirmed else []
    )
    if unconfirmed:
        assert data["unconfirmed"][0]["last_payment_date"] == ago(days)[0].isoformat()
        assert data["unconfirmed"][0]["amount"] == "15.99"


async def test_an_assumed_item_with_no_payment_at_all_is_unconfirmed(
    api, auth, frozen_now, make_entry, sessions, user_id
):
    netflix = await make_entry("Netflix")
    await assume(sessions, user_id, netflix)

    [item] = (await report(api, auth))["unconfirmed"]

    assert item["name"] == "Netflix"
    assert item["last_payment_date"] is None
    assert item["amount"] is None
    assert item["catalog_entry_id"] == str(netflix.id)


async def test_any_recent_bank_payment_confirms_not_only_detected_ones(
    api, auth, frozen_now, make_account, add_txn, make_entry, sessions, user_id
):
    acct = await make_account(user_id)
    netflix = await make_entry("Netflix")
    await assume(sessions, user_id, netflix)
    await add_txn(acct, "one-off", merchant_name="Netflix", date=ago(5)[0])

    assert (await report(api, auth))["unconfirmed"] == []


async def test_matching_uses_entity_ids_and_the_description(
    api, auth, frozen_now, make_account, add_txn, make_entry, sessions, user_id
):
    acct = await make_account(user_id)
    by_id = await make_entry("By id", aliases=[], merchant_entity_ids=["ent-7"])
    by_text = await make_entry("By text", aliases=["acme tv"])
    await assume(sessions, user_id, by_id, by_text)
    await add_txn(
        acct, "a", merchant_name="Whatever", merchant_entity_id="ent-7", date=ago(3)[0]
    )
    await add_txn(
        acct,
        "b",
        merchant_name=None,
        original_description="ACME TV 8842",
        date=ago(3)[0],
    )

    assert (await report(api, auth))["unconfirmed"] == []


async def test_pending_and_refunded_payments_do_not_confirm(
    api, auth, frozen_now, make_account, add_txn, make_entry, sessions, user_id
):
    from decimal import Decimal

    acct = await make_account(user_id)
    netflix = await make_entry("Netflix")
    await assume(sessions, user_id, netflix)
    await add_txn(acct, "p", merchant_name="Netflix", date=ago(2)[0], pending=True)
    await add_txn(
        acct, "r", merchant_name="Netflix", date=ago(2)[0], amount=Decimal("-15.99")
    )

    assert len((await report(api, auth))["unconfirmed"]) == 1


async def test_another_users_payments_do_not_confirm_mine(
    api,
    auth,
    frozen_now,
    make_account,
    add_txn,
    make_entry,
    sessions,
    user_id,
    other_user_id,
):
    theirs = await make_account(other_user_id)
    netflix = await make_entry("Netflix")
    await assume(sessions, user_id, netflix)
    await add_txn(theirs, "x", merchant_name="Netflix", date=ago(2)[0])

    assert len((await report(api, auth))["unconfirmed"]) == 1
