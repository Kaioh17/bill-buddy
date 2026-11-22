"""/plaid routes over HTTP, with the real app, a SQLite DB and FakePlaid."""

import json

import pytest

from app.auth.encryption import decrypt_token
from app.core.plaid import PlaidError
from app.models.linked_accounts import LinkedAccount
from app.models.transactions import Transaction
from tests.fakes import PLAIN_TOKEN, page, signed_webhook, txn

pytestmark = pytest.mark.anyio

EXCHANGE = {"public_token": "public-1", "institution_name": "Chase"}


@pytest.mark.parametrize(
    "path", ["/plaid/link-token", "/plaid/exchange", "/plaid/sandbox-link"]
)
async def test_routes_need_a_session(api, path):
    r = await api.post(path, json=EXCHANGE)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_authenticated"


# ---- link token ----


async def test_link_token_returns_the_token(api, auth, fake_plaid, user_id):
    r = await api.post("/plaid/link-token", headers=auth)
    assert r.status_code == 200
    assert r.json()["data"] == {
        "link_token": "link-sandbox-abc",
        "expiration": "2026-11-22T16:00:00Z",
    }
    assert fake_plaid.link_calls == [str(user_id)]  # the id comes from the session


async def test_link_token_failure_is_a_safe_502(api, auth, fake_plaid):
    fake_plaid.link_error = PlaidError("INTERNAL_SERVER_ERROR", "plaid internals")
    r = await api.post("/plaid/link-token", headers=auth)
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "bank_provider_error"
    assert "plaid internals" not in r.text


# ---- exchange ----


async def test_exchange_creates_the_account_and_never_returns_the_token(
    api, auth, fake_plaid, user_id, frozen_now, all_rows
):
    fake_plaid.pages = [page(added=[txn("t1")], cursor="c1")]
    r = await api.post("/plaid/exchange", json=EXCHANGE, headers=auth)

    assert r.status_code == 201
    data = r.json()["data"]
    assert data["institution_name"] == "Chase"
    assert data["status"] == "active"
    assert data["last_sync_at"] is not None
    for leaked in ("token", "enc", "cursor", PLAIN_TOKEN):
        assert leaked not in r.text

    [saved] = await all_rows(LinkedAccount)
    assert saved.user_id == user_id
    assert decrypt_token(saved.access_token_enc) == PLAIN_TOKEN
    assert len(await all_rows(Transaction)) == 1


async def test_exchange_still_succeeds_when_the_first_import_fails(
    api, auth, fake_plaid, frozen_now, all_rows
):
    fake_plaid.pages = [PlaidError("RATE_LIMIT_EXCEEDED")]
    r = await api.post("/plaid/exchange", json=EXCHANGE, headers=auth)

    assert r.status_code == 201
    assert r.json()["data"]["last_error"] == "RATE_LIMIT_EXCEEDED"
    assert len(await all_rows(LinkedAccount)) == 1


async def test_exchange_failure_is_a_502_and_saves_nothing(
    api, auth, fake_plaid, all_rows
):
    fake_plaid.exchange_error = PlaidError("INVALID_PUBLIC_TOKEN", "plaid internals")
    r = await api.post("/plaid/exchange", json=EXCHANGE, headers=auth)

    assert r.status_code == 502
    assert r.json()["error"]["code"] == "bank_provider_error"
    assert "plaid internals" not in r.text
    assert await all_rows(LinkedAccount) == []


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"public_token": "", "institution_name": "Chase"},
        {"public_token": "public-1"},
        {**EXCHANGE, "user_id": "someone-else"},  # the owner is never taken from input
    ],
)
async def test_exchange_validates_the_body(api, auth, fake_plaid, body):
    r = await api.post("/plaid/exchange", json=body, headers=auth)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert fake_plaid.exchanged == []


# ---- sandbox shortcut ----


async def test_sandbox_link_links_a_sandbox_bank(
    api, auth, fake_plaid, frozen_now, all_rows
):
    r = await api.post("/plaid/sandbox-link", headers=auth)
    assert r.status_code == 201
    assert r.json()["data"]["institution_name"] == "First Platypus Bank"
    assert fake_plaid.exchanged == ["public-sandbox-abc"]
    assert len(await all_rows(LinkedAccount)) == 1


async def test_sandbox_link_is_a_404_outside_the_sandbox(
    api, auth, fake_plaid, production_env
):
    r = await api.post("/plaid/sandbox-link", headers=auth)
    assert r.status_code == 404
    assert fake_plaid.exchanged == []


# ---- webhook (no session: Plaid calls it, the signature is the credential) ----

PAYLOAD = {
    "webhook_type": "TRANSACTIONS",
    "webhook_code": "SYNC_UPDATES_AVAILABLE",
    "item_id": "item-1",
}


def post_webhook(api, payload=PAYLOAD, **sign):
    body = json.dumps(payload).encode()
    return api.post(
        "/plaid/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "Plaid-Verification": signed_webhook(body, **sign),
        },
    )


async def test_signed_webhook_triggers_an_import(
    api, fake_plaid, make_account, user_id, frozen_now, all_rows
):
    await make_account(user_id)
    fake_plaid.pages = [page(added=[txn("t1")])]
    r = await post_webhook(api)

    assert r.status_code == 200
    assert len(await all_rows(Transaction)) == 1


async def test_webhook_without_a_signature_is_401(
    api, fake_plaid, make_account, user_id, frozen_now
):
    await make_account(user_id)
    r = await api.post("/plaid/webhook", json=PAYLOAD)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_webhook"
    assert fake_plaid.sync_calls == []


async def test_webhook_with_a_forged_signature_is_401(
    api, fake_plaid, make_account, user_id, frozen_now
):
    await make_account(user_id)
    r = await post_webhook(api, wrong_key=True)
    assert r.status_code == 401
    assert fake_plaid.sync_calls == []


async def test_webhook_for_an_unknown_item_is_still_200(api, fake_plaid, frozen_now):
    # Plaid retries on anything but 2xx, and an unknown item is not worth retrying.
    r = await post_webhook(api, PAYLOAD | {"item_id": "nope"})
    assert r.status_code == 200
    assert fake_plaid.sync_calls == []
