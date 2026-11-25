"""/subscriptions routes: list with labels and flags, confirm, dismiss."""

import uuid
from decimal import Decimal

import pytest

from app.models.assumed_entries import AssumedEntry
from app.models.matched_payments import MatchedPayment
from app.models.subscriptions import (
    DismissedSubscription,
    Frequency,
    Subscription,
    SubscriptionSource,
    SubscriptionStatus,
)

pytestmark = pytest.mark.anyio

MANUAL = {"source": SubscriptionSource.MANUAL, "merchant_key": None, "status": None}
LIKELY = {
    "status": SubscriptionStatus.LIKELY,
    "likely_reasons": ["amount changed, maybe a plan change"],
}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/subscriptions"),
        ("POST", f"/subscriptions/{uuid.uuid4()}/confirm"),
        ("POST", f"/subscriptions/{uuid.uuid4()}/dismiss"),
    ],
)
async def test_routes_need_a_session(api, method, path):
    r = await api.request(method, path)
    assert r.status_code == 401


# ---- list ----


async def test_list_has_labels_and_money_as_strings(api, auth, make_sub, user_id):
    await make_sub(user_id, name="Netflix", merchant_key="a")
    await make_sub(user_id, name="Spotify", merchant_key="b", **LIKELY)
    await make_sub(user_id, name="Gym", **MANUAL)

    r = await api.get("/subscriptions", headers=auth)

    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["count"] == 3
    by_name = {s["name"]: s for s in body["data"]}
    assert by_name["Netflix"]["label"] == "actual"
    assert by_name["Spotify"]["label"] == "likely"
    assert by_name["Spotify"]["likely_reasons"] == [
        "amount changed, maybe a plan change"
    ]
    assert by_name["Gym"]["label"] == "manual"
    assert by_name["Netflix"]["amount"] == "15.99"
    assert by_name["Netflix"]["frequency"] == "MONTHLY"
    assert by_name["Netflix"]["next_expected_date"] == "2026-12-12"


async def test_list_hides_inactive_and_other_peoples_rows(
    api, auth, make_sub, user_id, other_user_id
):
    await make_sub(user_id, name="Mine")
    await make_sub(user_id, name="Cancelled", merchant_key="x", is_active=False)
    await make_sub(other_user_id, name="Theirs", merchant_key="y")

    r = await api.get("/subscriptions", headers=auth)

    assert [s["name"] for s in r.json()["data"]] == ["Mine"]


async def test_list_flags_two_actual_subscriptions_of_one_service_type(
    api, auth, make_sub, user_id
):
    await make_sub(
        user_id, name="Spotify", merchant_key="a", service_type="Music streaming"
    )
    await make_sub(
        user_id, name="Apple Music", merchant_key="b", service_type="Music streaming"
    )
    await make_sub(
        user_id, name="Netflix", merchant_key="c", service_type="Video streaming"
    )
    await make_sub(
        user_id,
        name="Tidal",
        merchant_key="d",
        service_type="Music streaming",
        **LIKELY,
    )

    r = await api.get("/subscriptions", headers=auth)

    by_name = {s["name"]: s for s in r.json()["data"]}
    assert by_name["Spotify"]["similar_to"] == ["Apple Music"]
    assert by_name["Apple Music"]["similar_to"] == ["Spotify"]
    assert by_name["Netflix"]["similar_to"] == []
    assert by_name["Tidal"]["similar_to"] == []  # likely items are not counted


async def test_list_does_not_flag_a_single_subscription(api, auth, make_sub, user_id):
    await make_sub(user_id, service_type="Music streaming")
    r = await api.get("/subscriptions", headers=auth)
    assert r.json()["data"][0]["similar_to"] == []


async def test_list_says_whether_it_is_on_the_assumed_list(
    api, auth, make_sub, make_entry, sessions, user_id
):
    entry = await make_entry("Netflix")
    await make_sub(user_id, name="Netflix", merchant_key="a", catalog_entry_id=entry.id)
    await make_sub(user_id, name="Spotify", merchant_key="b")
    async with sessions() as s:
        s.add(AssumedEntry(user_id=user_id, catalog_entry_id=entry.id))
        await s.commit()

    r = await api.get("/subscriptions", headers=auth)

    by_name = {s["name"]: s for s in r.json()["data"]}
    assert by_name["Netflix"]["on_assumed_list"] is True
    assert by_name["Spotify"]["on_assumed_list"] is False


# ---- confirm ----


async def test_confirm_makes_a_likely_item_actual(api, auth, make_sub, user_id, fetch):
    sub = await make_sub(user_id, **LIKELY)

    r = await api.post(f"/subscriptions/{sub.id}/confirm", headers=auth)

    assert r.status_code == 204
    row = await fetch(Subscription, sub.id)
    assert row.status == SubscriptionStatus.ACTUAL
    assert row.likely_reasons == []


@pytest.mark.parametrize("action", ["confirm", "dismiss"])
async def test_an_actual_item_cannot_be_confirmed_or_dismissed(
    api, auth, make_sub, user_id, action
):
    sub = await make_sub(user_id)
    r = await api.post(f"/subscriptions/{sub.id}/{action}", headers=auth)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "not_likely"


@pytest.mark.parametrize("action", ["confirm", "dismiss"])
async def test_someone_elses_or_a_manual_or_a_missing_item_is_a_404(
    api, auth, make_sub, user_id, other_user_id, action
):
    theirs = await make_sub(other_user_id, **LIKELY)
    manual = await make_sub(user_id, **MANUAL)
    for sub_id in (theirs.id, manual.id, uuid.uuid4()):
        r = await api.post(f"/subscriptions/{sub_id}/{action}", headers=auth)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "not_found"


# ---- dismiss ----


async def test_dismiss_removes_it_and_remembers_the_rejection(
    api, auth, make_sub, sessions, user_id, all_rows
):
    sub = await make_sub(user_id, merchant_key="name:netflix", **LIKELY)
    async with sessions() as s:
        s.add(
            MatchedPayment(
                subscription_id=sub.id,
                user_id=user_id,
                transaction_id="t1",
                date=sub.last_payment_date,
                amount=Decimal("15.99"),
                merchant_name="Netflix",
            )
        )
        await s.commit()

    r = await api.post(f"/subscriptions/{sub.id}/dismiss", headers=auth)

    assert r.status_code == 204
    assert await all_rows(Subscription) == []
    assert await all_rows(MatchedPayment) == []
    [d] = await all_rows(DismissedSubscription)
    assert (d.user_id, d.merchant_key, d.frequency) == (
        user_id,
        "name:netflix",
        Frequency.MONTHLY,
    )


async def test_dismissing_twice_in_a_row_is_a_404_not_a_crash(
    api, auth, make_sub, user_id
):
    sub = await make_sub(user_id, **LIKELY)
    await api.post(f"/subscriptions/{sub.id}/dismiss", headers=auth)
    r = await api.post(f"/subscriptions/{sub.id}/dismiss", headers=auth)
    assert r.status_code == 404
