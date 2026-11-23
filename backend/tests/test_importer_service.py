"""import_account: the rules for what gets stored, and what happens when it fails."""

import datetime as dt
from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.exception import (
    ReconnectRequiredError,
    SyncFailedError,
    SyncInProgressError,
)
from app.core.plaid import PlaidError
from app.models.linked_accounts import LinkedAccount, LinkStatus
from app.models.transactions import Transaction
from app.services.importer import import_account
from tests.fakes import PLAIN_TOKEN, as_utc, minutes_ago, page, txn

pytestmark = pytest.mark.anyio


@pytest.fixture
async def account(make_account, user_id):
    return await make_account(user_id)


@pytest.fixture
def run(sessions, fake_plaid, frozen_now):
    async def go(account_id):
        async with sessions() as s:
            acct = await s.get(LinkedAccount, account_id)
            return await import_account(s, fake_plaid, acct)

    return go


async def ids(all_rows):
    return sorted(t.transaction_id for t in await all_rows(Transaction))


# ---- what gets stored ----


async def test_stores_added_transactions_with_fields_mapped(
    run, fake_plaid, account, user_id, all_rows
):
    fake_plaid.pages = [page(added=[txn("t1", amount=12.5, date="2026-11-01")])]
    result = await run(account.id)

    assert (result.added, result.modified, result.removed) == (1, 0, 0)
    [row] = await all_rows(Transaction)
    assert row.transaction_id == "t1"
    assert row.amount == Decimal("12.50")
    assert row.date == dt.date(2026, 11, 1)
    assert row.pending is False
    assert row.user_id == user_id
    assert row.linked_account_id == account.id
    assert row.plaid_account_id == "acc-1"
    assert row.iso_currency_code == "USD"
    assert row.merchant_name == "Netflix"
    assert row.merchant_entity_id == "ent-1"
    assert row.pfc_primary == "ENTERTAINMENT"
    assert row.pfc_detailed == "ENTERTAINMENT_TV_AND_MOVIES"


async def test_missing_merchant_and_category_are_stored_as_null(
    run, fake_plaid, account, all_rows
):
    fake_plaid.pages = [page(added=[txn("t1", merchant=None, pfc=None)])]
    await run(account.id)
    [row] = await all_rows(Transaction)
    assert row.merchant_name is None and row.pfc_primary is None


async def test_pending_transactions_are_skipped(run, fake_plaid, account, all_rows):
    fake_plaid.pages = [page(added=[txn("t1", pending=True), txn("t2")])]
    result = await run(account.id)
    assert await ids(all_rows) == ["t2"]
    assert result.added == 1


async def test_older_than_12_months_is_skipped_and_the_boundary_day_is_kept(
    run, fake_plaid, account, all_rows
):
    # "Today" is 2026-11-22, so 2025-11-22 is the oldest day kept.
    fake_plaid.pages = [
        page(
            added=[
                txn("old", date="2025-11-21"),
                txn("edge", date="2025-11-22"),
                txn("new", date="2026-11-21"),
            ]
        )
    ]
    await run(account.id)
    assert await ids(all_rows) == ["edge", "new"]


async def test_importing_the_same_page_twice_adds_no_duplicates(
    run, fake_plaid, account, all_rows
):
    fake_plaid.pages = [page(added=[txn("t1")]), page(added=[txn("t1")])]
    await run(account.id)
    second = await run(account.id)
    assert await ids(all_rows) == ["t1"]
    assert second.added == 0


async def test_duplicate_ids_inside_one_batch_are_stored_once(
    run, fake_plaid, account, all_rows
):
    fake_plaid.pages = [page(added=[txn("t1"), txn("t1")])]
    result = await run(account.id)
    assert await ids(all_rows) == ["t1"]
    assert result.added == 1


async def test_modified_updates_the_stored_row(
    run, fake_plaid, account, add_txn, all_rows
):
    await add_txn(account, "t1", amount=Decimal("9.99"))
    fake_plaid.pages = [page(modified=[txn("t1", amount=15.0)])]
    result = await run(account.id)

    [row] = await all_rows(Transaction)
    assert row.amount == Decimal("15.00")
    assert result.modified == 1


async def test_removed_deletes_the_row(run, fake_plaid, account, add_txn, all_rows):
    await add_txn(account, "t1")
    await add_txn(account, "t2")
    fake_plaid.pages = [page(removed=["t1"])]
    result = await run(account.id)
    assert await ids(all_rows) == ["t2"]
    assert result.removed == 1


async def test_removed_never_touches_another_accounts_rows(
    run, fake_plaid, account, make_account, other_user_id, add_txn, all_rows
):
    other = await make_account(other_user_id, plaid_item_id="item-2")
    await add_txn(other, "theirs")
    fake_plaid.pages = [page(removed=["theirs"])]
    await run(account.id)
    assert await ids(all_rows) == ["theirs"]


# ---- cursor and pagination ----


async def test_first_import_has_no_cursor_and_the_stored_cursor_is_reused(
    run, fake_plaid, make_account, user_id
):
    fresh = await make_account(user_id)
    resumed = await make_account(user_id, plaid_item_id="item-2", cursor="saved-9")
    await run(fresh.id)
    await run(resumed.id)
    assert fake_plaid.sync_calls == [(PLAIN_TOKEN, None), (PLAIN_TOKEN, "saved-9")]


async def test_follows_has_more_and_saves_the_last_cursor(
    run, fake_plaid, account, fetch, all_rows
):
    fake_plaid.pages = [
        page(added=[txn("t1")], cursor="c1", has_more=True),
        page(added=[txn("t2")], cursor="c2", has_more=False),
    ]
    result = await run(account.id)

    assert [c for _, c in fake_plaid.sync_calls] == [None, "c1"]
    assert (await fetch(LinkedAccount, account.id)).cursor == "c2"
    assert await ids(all_rows) == ["t1", "t2"]
    assert result.added == 2


# ---- success bookkeeping ----


async def test_success_records_sync_state(
    run, fake_plaid, make_account, user_id, fetch, frozen_now
):
    acct = await make_account(
        user_id,
        last_error="RATE_LIMIT_EXCEEDED",
        sync_failures=2,
        next_sync=frozen_now,
    )
    fake_plaid.pages = [page(status="HISTORICAL_UPDATE_COMPLETE")]
    await run(acct.id)

    row = await fetch(LinkedAccount, acct.id)
    assert as_utc(row.last_sync_at) == frozen_now
    assert as_utc(row.next_sync) == frozen_now + timedelta(hours=24)
    assert row.last_error is None
    assert row.sync_failures == 0
    assert row.status == LinkStatus.ACTIVE
    assert row.history_ready is True
    assert row.sync_locked_at is None


async def test_history_is_not_ready_until_plaid_says_so(
    run, fake_plaid, account, fetch
):
    fake_plaid.pages = [page(status="NOT_READY")]
    await run(account.id)
    assert (await fetch(LinkedAccount, account.id)).history_ready is False


# ---- failure: rollback, retry schedule, reauth ----


async def test_failure_on_a_later_page_stores_nothing_and_keeps_the_old_cursor(
    run, fake_plaid, make_account, user_id, add_txn, fetch, all_rows
):
    acct = await make_account(user_id, cursor="old-cursor")
    await add_txn(acct, "keep-me")
    fake_plaid.pages = [
        page(added=[txn("t1")], removed=["keep-me"], cursor="c1", has_more=True),
        PlaidError("INTERNAL_SERVER_ERROR"),
    ]
    with pytest.raises(SyncFailedError):
        await run(acct.id)

    assert await ids(all_rows) == ["keep-me"]
    assert (await fetch(LinkedAccount, acct.id)).cursor == "old-cursor"


async def test_a_bad_row_rolls_back_the_good_rows_before_it(
    run, fake_plaid, make_account, user_id, fetch, all_rows
):
    acct = await make_account(user_id, cursor="old-cursor")
    fake_plaid.pages = [
        page(added=[txn("good"), txn("bad", date="not-a-date")], cursor="c1")
    ]
    with pytest.raises(SyncFailedError):
        await run(acct.id)

    assert await ids(all_rows) == []
    row = await fetch(LinkedAccount, acct.id)
    assert row.cursor == "old-cursor"
    assert row.sync_failures == 1
    assert row.sync_locked_at is None


async def test_temporary_failures_back_off_15m_1h_4h_then_24h(
    run, fake_plaid, account, fetch, frozen_now
):
    expected = [
        timedelta(minutes=15),
        timedelta(hours=1),
        timedelta(hours=4),
        timedelta(hours=24),
        timedelta(hours=24),
    ]
    for n, delay in enumerate(expected, start=1):
        fake_plaid.pages = [PlaidError("RATE_LIMIT_EXCEEDED")]
        with pytest.raises(SyncFailedError):
            await run(account.id)
        row = await fetch(LinkedAccount, account.id)
        assert row.sync_failures == n
        assert as_utc(row.next_sync) == frozen_now + delay
        assert row.last_error == "RATE_LIMIT_EXCEEDED"
        assert row.status == LinkStatus.ACTIVE
        assert row.sync_locked_at is None


async def test_permanent_failure_needs_reauth_and_is_not_retried(
    run, fake_plaid, account, fetch
):
    fake_plaid.pages = [PlaidError("ITEM_LOGIN_REQUIRED")]
    with pytest.raises(ReconnectRequiredError):
        await run(account.id)

    row = await fetch(LinkedAccount, account.id)
    assert row.status == LinkStatus.NEEDS
    assert row.next_sync is None
    assert row.last_error == "ITEM_LOGIN_REQUIRED"
    assert row.sync_locked_at is None


# ---- per-account lock ----


async def test_a_fresh_lock_blocks_the_import_without_calling_plaid(
    run, fake_plaid, make_account, user_id, frozen_now
):
    acct = await make_account(user_id, sync_locked_at=minutes_ago(1))
    with pytest.raises(SyncInProgressError):
        await run(acct.id)
    assert fake_plaid.sync_calls == []


async def test_a_stale_lock_is_taken_over(
    run, fake_plaid, make_account, user_id, fetch
):
    acct = await make_account(user_id, sync_locked_at=minutes_ago(11))
    await run(acct.id)
    assert len(fake_plaid.sync_calls) == 1
    assert (await fetch(LinkedAccount, acct.id)).sync_locked_at is None


async def test_the_lock_does_not_leak_into_other_accounts(
    run, fake_plaid, make_account, user_id
):
    locked = await make_account(user_id, sync_locked_at=minutes_ago(1))
    free = await make_account(user_id, plaid_item_id="item-2")
    await run(free.id)
    with pytest.raises(SyncInProgressError):
        await run(locked.id)
