"""Accounts service: list, sync now and disconnect, always scoped to the user."""

import uuid

import pytest

from app.core.exception import (
    BankProviderError,
    NotFoundError,
    ReconnectRequiredError,
)
from app.core.plaid import PlaidError
from app.models.linked_accounts import LinkedAccount, LinkStatus
from app.models.transactions import Transaction
from app.services import accounts as service
from tests.fakes import PLAIN_TOKEN, as_utc, page, txn

pytestmark = pytest.mark.anyio


# ---- list ----


async def test_list_returns_only_the_users_connected_accounts(
    session, make_account, user_id, other_user_id
):
    mine = await make_account(user_id)
    await make_account(user_id, status=LinkStatus.DISCONNECTED)
    await make_account(other_user_id)

    rows = await service.list_accounts(session, user_id)
    assert [r.id for r in rows] == [mine.id]


async def test_list_keeps_accounts_that_need_reauth(session, make_account, user_id):
    await make_account(user_id, status=LinkStatus.NEEDS)
    rows = await service.list_accounts(session, user_id)
    assert [r.status for r in rows] == [LinkStatus.NEEDS]


# ---- sync now ----


async def test_sync_now_returns_counts_and_the_last_sync_time(
    session, fake_plaid, make_account, user_id, frozen_now
):
    acct = await make_account(user_id)
    fake_plaid.pages = [page(added=[txn("t1"), txn("t2")])]
    out = await service.sync_now(session, fake_plaid, user_id, acct.id)

    assert (out.added, out.modified, out.removed) == (2, 0, 0)
    assert as_utc(out.last_sync_at) == frozen_now


@pytest.mark.parametrize("who", ["other_user", "unknown_id", "disconnected"])
async def test_sync_now_is_not_found_for_anything_that_is_not_the_users_live_account(
    session, fake_plaid, make_account, user_id, other_user_id, who
):
    if who == "other_user":
        target = (await make_account(other_user_id)).id
    elif who == "disconnected":
        target = (await make_account(user_id, status=LinkStatus.DISCONNECTED)).id
    else:
        target = uuid.uuid4()

    with pytest.raises(NotFoundError):
        await service.sync_now(session, fake_plaid, user_id, target)
    assert fake_plaid.sync_calls == []


async def test_sync_now_refuses_an_account_that_needs_reauth(
    session, fake_plaid, make_account, user_id
):
    acct = await make_account(user_id, status=LinkStatus.NEEDS)
    with pytest.raises(ReconnectRequiredError):
        await service.sync_now(session, fake_plaid, user_id, acct.id)
    assert fake_plaid.sync_calls == []


# ---- disconnect ----


async def test_disconnect_revokes_the_token_and_keeps_transactions_by_default(
    session, fake_plaid, make_account, user_id, add_txn, fetch, all_rows
):
    acct = await make_account(user_id)
    await add_txn(acct, "t1")
    await service.disconnect(session, fake_plaid, user_id, acct.id, False)

    assert fake_plaid.removed == [PLAIN_TOKEN]
    row = await fetch(LinkedAccount, acct.id)
    assert row.status == LinkStatus.DISCONNECTED
    assert row.access_token_enc == b""
    assert row.next_sync is None
    assert len(await all_rows(Transaction)) == 1


async def test_disconnect_can_delete_that_accounts_transactions_only(
    session, fake_plaid, make_account, user_id, other_user_id, add_txn, all_rows
):
    acct = await make_account(user_id)
    other = await make_account(other_user_id, plaid_item_id="item-2")
    await add_txn(acct, "mine")
    await add_txn(other, "theirs")
    await service.disconnect(session, fake_plaid, user_id, acct.id, True)

    assert [t.transaction_id for t in await all_rows(Transaction)] == ["theirs"]


async def test_disconnect_carries_on_when_plaid_has_already_dropped_the_item(
    session, fake_plaid, make_account, user_id, fetch
):
    acct = await make_account(user_id)
    fake_plaid.remove_error = PlaidError("ITEM_NOT_FOUND")
    await service.disconnect(session, fake_plaid, user_id, acct.id, False)
    assert (await fetch(LinkedAccount, acct.id)).status == LinkStatus.DISCONNECTED


async def test_disconnect_stops_when_the_token_could_not_be_revoked(
    session, fake_plaid, make_account, user_id, add_txn, fetch, all_rows
):
    acct = await make_account(user_id)
    await add_txn(acct, "t1")
    fake_plaid.remove_error = PlaidError("INTERNAL_SERVER_ERROR")
    with pytest.raises(BankProviderError):
        await service.disconnect(session, fake_plaid, user_id, acct.id, True)

    row = await fetch(LinkedAccount, acct.id)
    assert row.status == LinkStatus.ACTIVE
    assert row.access_token_enc != b""
    assert len(await all_rows(Transaction)) == 1


async def test_disconnect_is_not_found_for_another_users_account(
    session, fake_plaid, make_account, user_id, other_user_id, fetch
):
    theirs = await make_account(other_user_id)
    with pytest.raises(NotFoundError):
        await service.disconnect(session, fake_plaid, user_id, theirs.id, True)
    assert fake_plaid.removed == []
    assert (await fetch(LinkedAccount, theirs.id)).status == LinkStatus.ACTIVE
