"""/accounts routes over HTTP, with the real app, a SQLite DB and FakePlaid."""

import uuid

import pytest

from app.core.plaid import PlaidError
from app.models.linked_accounts import LinkedAccount, LinkStatus
from app.models.transactions import Transaction
from tests.fakes import PLAIN_TOKEN, page, txn

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/accounts"),
        ("POST", f"/accounts/{uuid.uuid4()}/sync"),
        ("DELETE", f"/accounts/{uuid.uuid4()}"),
    ],
)
async def test_routes_need_a_session(api, method, path):
    r = await api.request(method, path)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_authenticated"


# ---- list ----


async def test_list_shows_only_my_connected_accounts(
    api, auth, make_account, user_id, other_user_id
):
    mine = await make_account(user_id, institution_name="Chase")
    await make_account(user_id, status=LinkStatus.DISCONNECTED)
    await make_account(other_user_id, institution_name="Not Mine")

    r = await api.get("/accounts", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["count"] == 1
    [item] = body["data"]
    assert item["id"] == str(mine.id)
    assert item["institution_name"] == "Chase"
    assert item["status"] == "active"
    assert {"last_sync_at", "next_sync", "last_error", "history_ready"} <= item.keys()


async def test_list_never_exposes_secrets(api, auth, make_account, user_id):
    await make_account(user_id, cursor="secret-cursor")
    r = await api.get("/accounts", headers=auth)
    for leaked in ("token", "enc", "cursor", PLAIN_TOKEN, "plaid_item_id"):
        assert leaked not in r.text


async def test_list_is_empty_for_a_new_user(api, auth):
    r = await api.get("/accounts", headers=auth)
    assert r.json()["data"] == []
    assert r.json()["meta"]["count"] == 0


async def test_list_shows_reauth_state(api, auth, make_account, user_id):
    await make_account(
        user_id, status=LinkStatus.NEEDS, last_error="ITEM_LOGIN_REQUIRED"
    )
    [item] = (await api.get("/accounts", headers=auth)).json()["data"]
    assert item["status"] == "needs_reauth"
    assert item["last_error"] == "ITEM_LOGIN_REQUIRED"


# ---- sync now ----


async def test_sync_now_returns_the_last_sync_time_and_counts(
    api, auth, fake_plaid, make_account, user_id, frozen_now
):
    acct = await make_account(user_id)
    fake_plaid.pages = [page(added=[txn("t1")])]
    r = await api.post(f"/accounts/{acct.id}/sync", headers=auth)

    assert r.status_code == 200
    data = r.json()["data"]
    assert data["added"] == 1 and data["modified"] == 0 and data["removed"] == 0
    assert data["last_sync_at"].startswith("2026-11-22T12:00:00")


async def test_sync_now_on_someone_elses_account_is_404(
    api, auth, fake_plaid, make_account, other_user_id
):
    theirs = await make_account(other_user_id)
    r = await api.post(f"/accounts/{theirs.id}/sync", headers=auth)
    assert r.status_code == 404
    assert fake_plaid.sync_calls == []


async def test_sync_now_with_a_malformed_id_is_422(api, auth):
    r = await api.post("/accounts/not-a-uuid/sync", headers=auth)
    assert r.status_code == 422


async def test_sync_now_failure_is_502_and_the_old_data_stays(
    api, auth, fake_plaid, make_account, user_id, add_txn, fetch, all_rows, frozen_now
):
    acct = await make_account(user_id)
    await add_txn(acct, "keep-me")
    fake_plaid.pages = [PlaidError("INTERNAL_SERVER_ERROR")]
    r = await api.post(f"/accounts/{acct.id}/sync", headers=auth)

    assert r.status_code == 502
    err = r.json()["error"]
    assert err["code"] == "sync_failed"
    assert "out of date" in err["message"]
    assert [t.transaction_id for t in await all_rows(Transaction)] == ["keep-me"]
    assert (await fetch(LinkedAccount, acct.id)).last_error == "INTERNAL_SERVER_ERROR"


async def test_sync_now_with_an_expired_bank_login_asks_to_reconnect(
    api, auth, fake_plaid, make_account, user_id, fetch, frozen_now
):
    acct = await make_account(user_id)
    fake_plaid.pages = [PlaidError("ITEM_LOGIN_REQUIRED")]
    r = await api.post(f"/accounts/{acct.id}/sync", headers=auth)

    assert r.status_code == 409
    assert r.json()["error"]["code"] == "reconnect_required"
    assert (await fetch(LinkedAccount, acct.id)).status == LinkStatus.NEEDS

    # Once flagged, Plaid is not called again until the user reconnects.
    fake_plaid.sync_calls.clear()
    again = await api.post(f"/accounts/{acct.id}/sync", headers=auth)
    assert again.status_code == 409
    assert fake_plaid.sync_calls == []


async def test_sync_now_while_another_sync_runs_is_409(
    api, auth, fake_plaid, make_account, user_id, frozen_now
):
    from tests.fakes import minutes_ago

    acct = await make_account(user_id, sync_locked_at=minutes_ago(1))
    r = await api.post(f"/accounts/{acct.id}/sync", headers=auth)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "sync_in_progress"
    assert fake_plaid.sync_calls == []


# ---- disconnect ----


async def test_disconnect_returns_204_and_hides_the_account(
    api, auth, fake_plaid, make_account, user_id, add_txn, all_rows
):
    acct = await make_account(user_id)
    await add_txn(acct, "t1")
    r = await api.delete(f"/accounts/{acct.id}", headers=auth)

    assert r.status_code == 204
    assert fake_plaid.removed == [PLAIN_TOKEN]
    assert (await api.get("/accounts", headers=auth)).json()["data"] == []
    assert len(await all_rows(Transaction)) == 1  # kept unless asked


async def test_disconnect_can_delete_the_transactions(
    api, auth, make_account, user_id, add_txn, all_rows
):
    acct = await make_account(user_id)
    await add_txn(acct, "t1")
    r = await api.delete(f"/accounts/{acct.id}?delete_transactions=true", headers=auth)

    assert r.status_code == 204
    assert await all_rows(Transaction) == []


async def test_disconnect_on_someone_elses_account_is_404_and_changes_nothing(
    api, auth, fake_plaid, make_account, other_user_id, add_txn, fetch, all_rows
):
    theirs = await make_account(other_user_id)
    await add_txn(theirs, "t1")
    r = await api.delete(
        f"/accounts/{theirs.id}?delete_transactions=true", headers=auth
    )

    assert r.status_code == 404
    assert fake_plaid.removed == []
    assert (await fetch(LinkedAccount, theirs.id)).status == LinkStatus.ACTIVE
    assert len(await all_rows(Transaction)) == 1


async def test_disconnect_failure_is_502_and_the_account_stays_connected(
    api, auth, fake_plaid, make_account, user_id, fetch
):
    acct = await make_account(user_id)
    fake_plaid.remove_error = PlaidError("INTERNAL_SERVER_ERROR")
    r = await api.delete(f"/accounts/{acct.id}", headers=auth)

    assert r.status_code == 502
    assert (await fetch(LinkedAccount, acct.id)).status == LinkStatus.ACTIVE


async def test_a_disconnected_account_cannot_be_synced(
    api, auth, fake_plaid, make_account, user_id
):
    acct = await make_account(user_id)
    await api.delete(f"/accounts/{acct.id}", headers=auth)
    r = await api.post(f"/accounts/{acct.id}/sync", headers=auth)
    assert r.status_code == 404
