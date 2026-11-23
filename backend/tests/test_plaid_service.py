"""Plaid service: link token, exchange, sandbox shortcut and webhook handling."""

import json

import pytest

from app.auth.encryption import decrypt_token
from app.core.exception import BankProviderError, InvalidWebhookError, NotFoundError
from app.core.plaid import PlaidError
from app.models.linked_accounts import LinkedAccount, LinkStatus
from app.models.transactions import Transaction
from app.schema.plaid import ExchangeRequest
from app.services import plaid as service
from tests.fakes import PLAIN_TOKEN, minutes_ago, page, signed_webhook, txn

pytestmark = pytest.mark.anyio

EXCHANGE = ExchangeRequest(public_token="public-1", institution_name="Chase")


# ---- link token ----


async def test_link_token_is_created_for_the_given_user(fake_plaid, user_id):
    out = await service.create_link_token(fake_plaid, user_id)
    assert out.link_token == "link-sandbox-abc"
    assert out.expiration == "2026-11-22T16:00:00Z"
    assert fake_plaid.link_calls == [str(user_id)]


async def test_link_token_failure_is_hidden_behind_a_safe_error(fake_plaid, user_id):
    fake_plaid.link_error = PlaidError("INTERNAL_SERVER_ERROR", "plaid internals")
    with pytest.raises(BankProviderError) as err:
        await service.create_link_token(fake_plaid, user_id)
    assert "plaid internals" not in err.value.message


# ---- exchange ----


async def test_exchange_saves_the_account_with_an_encrypted_token(
    session, fake_plaid, user_id, frozen_now
):
    account = await service.exchange(session, fake_plaid, user_id, EXCHANGE)

    assert fake_plaid.exchanged == ["public-1"]
    assert account.user_id == user_id
    assert account.institution_name == "Chase"
    assert account.plaid_item_id == "item-1"
    assert account.status == LinkStatus.ACTIVE
    assert PLAIN_TOKEN.encode() not in account.access_token_enc
    assert decrypt_token(account.access_token_enc) == PLAIN_TOKEN


async def test_exchange_runs_the_first_import(
    session, fake_plaid, user_id, frozen_now, all_rows
):
    fake_plaid.pages = [page(added=[txn("t1"), txn("t2")], cursor="c1")]
    account = await service.exchange(session, fake_plaid, user_id, EXCHANGE)

    assert len(await all_rows(Transaction)) == 2
    assert account.cursor == "c1"
    assert account.last_sync_at is not None


async def test_exchange_keeps_the_account_when_the_first_import_fails(
    session, fake_plaid, user_id, frozen_now, all_rows
):
    fake_plaid.pages = [PlaidError("RATE_LIMIT_EXCEEDED")]
    account = await service.exchange(session, fake_plaid, user_id, EXCHANGE)

    assert len(await all_rows(LinkedAccount)) == 1
    assert account.status == LinkStatus.ACTIVE
    assert account.last_error == "RATE_LIMIT_EXCEEDED"
    assert account.next_sync is not None  # picked up by the retry schedule


async def test_exchange_failure_saves_nothing(
    session, fake_plaid, user_id, frozen_now, all_rows
):
    fake_plaid.exchange_error = PlaidError("INVALID_PUBLIC_TOKEN", "plaid internals")
    with pytest.raises(BankProviderError) as err:
        await service.exchange(session, fake_plaid, user_id, EXCHANGE)

    assert await all_rows(LinkedAccount) == []
    assert "plaid internals" not in err.value.message


# ---- sandbox shortcut ----


async def test_sandbox_link_creates_a_sandbox_item_and_links_it(
    session, fake_plaid, user_id, frozen_now
):
    account = await service.sandbox_link(session, fake_plaid, user_id)
    assert fake_plaid.exchanged == ["public-sandbox-abc"]
    assert account.institution_name == "First Platypus Bank"
    assert account.user_id == user_id


async def test_sandbox_link_does_not_exist_outside_the_sandbox(
    session, fake_plaid, user_id, production_env
):
    with pytest.raises(NotFoundError):
        await service.sandbox_link(session, fake_plaid, user_id)
    assert fake_plaid.exchanged == []


# ---- webhook signature ----

BODY = json.dumps({"webhook_type": "TRANSACTIONS"}).encode()


async def test_a_correctly_signed_webhook_is_accepted(fake_plaid, frozen_now):
    await service.verify_webhook(fake_plaid, BODY, signed_webhook(BODY))


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(None, id="missing"),
        pytest.param("not-a-jwt", id="garbage"),
        pytest.param(signed_webhook(BODY, wrong_key=True), id="wrong-signing-key"),
        pytest.param(signed_webhook(BODY, alg="HS256"), id="wrong-algorithm"),
        pytest.param(
            signed_webhook(BODY, body_hash=b"something else"), id="body-hash-mismatch"
        ),
        pytest.param(signed_webhook(BODY, iat=minutes_ago(6)), id="older-than-5-min"),
    ],
)
async def test_bad_webhook_signatures_are_rejected(fake_plaid, frozen_now, token):
    with pytest.raises(InvalidWebhookError):
        await service.verify_webhook(fake_plaid, BODY, token)


async def test_a_tampered_body_is_rejected(fake_plaid, frozen_now):
    token = signed_webhook(BODY)
    with pytest.raises(InvalidWebhookError):
        await service.verify_webhook(fake_plaid, BODY + b" ", token)


async def test_webhook_is_rejected_when_the_verification_key_cannot_be_fetched(
    fake_plaid, frozen_now
):
    fake_plaid.webhook_key_error = PlaidError("INTERNAL_SERVER_ERROR")
    with pytest.raises(InvalidWebhookError):
        await service.verify_webhook(fake_plaid, BODY, signed_webhook(BODY))


# ---- webhook handling ----

UPDATES = {
    "webhook_type": "TRANSACTIONS",
    "webhook_code": "SYNC_UPDATES_AVAILABLE",
    "item_id": "item-1",
}


async def test_sync_updates_webhook_imports_the_item(
    session, fake_plaid, make_account, user_id, frozen_now, all_rows
):
    await make_account(user_id)
    fake_plaid.pages = [page(added=[txn("t1")])]
    await service.handle_webhook(session, fake_plaid, UPDATES)
    assert len(await all_rows(Transaction)) == 1


async def test_webhook_for_an_unknown_item_is_ignored(session, fake_plaid, frozen_now):
    await service.handle_webhook(session, fake_plaid, UPDATES | {"item_id": "nope"})
    assert fake_plaid.sync_calls == []


@pytest.mark.parametrize(
    "payload",
    [
        UPDATES | {"webhook_code": "RECURRING_TRANSACTIONS_UPDATE"},
        UPDATES | {"webhook_type": "ITEM"},
        {"webhook_type": "TRANSACTIONS"},
    ],
)
async def test_other_webhook_types_are_ignored(
    session, fake_plaid, make_account, user_id, frozen_now, payload
):
    await make_account(user_id)
    await service.handle_webhook(session, fake_plaid, payload)
    assert fake_plaid.sync_calls == []


@pytest.mark.parametrize("status", [LinkStatus.NEEDS, LinkStatus.DISCONNECTED])
async def test_webhook_skips_accounts_that_are_not_active(
    session, fake_plaid, make_account, user_id, frozen_now, status
):
    await make_account(user_id, status=status)
    await service.handle_webhook(session, fake_plaid, UPDATES)
    assert fake_plaid.sync_calls == []


async def test_a_failed_import_does_not_fail_the_webhook(
    session, fake_plaid, make_account, user_id, frozen_now, fetch
):
    acct = await make_account(user_id)
    fake_plaid.pages = [PlaidError("RATE_LIMIT_EXCEEDED")]
    await service.handle_webhook(session, fake_plaid, UPDATES)  # must not raise
    assert (await fetch(LinkedAccount, acct.id)).last_error == "RATE_LIMIT_EXCEEDED"
