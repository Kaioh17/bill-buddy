"""Detection runs after every import, and can never fail one."""

import pytest

from app.models.linked_accounts import LinkedAccount
from app.models.subscriptions import Subscription
from app.services import detection, importer
from tests.fakes import ago, page, txn

pytestmark = pytest.mark.anyio


def monthly_netflix():
    return [
        txn(f"n{i}", date=d.isoformat(), amount=15.99, merchant="Netflix")
        for i, d in enumerate(ago(70, 40, 10))
    ]


async def test_an_import_detects_subscriptions(
    session, fake_plaid, frozen_now, make_account, user_id, all_rows
):
    acct = await make_account(user_id)
    fake_plaid.pages = [page(added=monthly_netflix())]

    await importer.import_account(
        session, fake_plaid, await session.get(LinkedAccount, acct.id)
    )

    [sub] = await all_rows(Subscription)
    assert sub.name == "Netflix"


async def test_a_detection_crash_does_not_fail_the_import(
    session, fake_plaid, frozen_now, make_account, user_id, fetch, monkeypatch
):
    acct = await make_account(user_id)
    fake_plaid.pages = [page(added=monthly_netflix(), cursor="c9")]

    async def boom(*args, **kwargs):
        raise RuntimeError("detector bug")

    monkeypatch.setattr(detection, "detect_subscriptions", boom)

    result = await importer.import_account(
        session, fake_plaid, await session.get(LinkedAccount, acct.id)
    )

    assert result.added == 3
    assert (await fetch(LinkedAccount, acct.id)).cursor == "c9"
