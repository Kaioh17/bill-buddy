"""/catalog and /assumed: the picker and the saved assumed list (FR 2b, TC-07)."""

import uuid

import pytest

from app.models.assumed_entries import AssumedEntry

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(("method", "path"), [("GET", "/catalog"), ("PUT", "/assumed")])
async def test_routes_need_a_session(api, method, path):
    assert (await api.request(method, path)).status_code == 401


async def test_catalog_lists_entries_with_my_selection(
    api, auth, make_entry, sessions, user_id, other_user_id
):
    netflix = await make_entry("Netflix")
    await make_entry("Spotify", service_type="Music streaming")
    async with sessions() as s:
        s.add(AssumedEntry(user_id=user_id, catalog_entry_id=netflix.id))
        s.add(AssumedEntry(user_id=other_user_id, catalog_entry_id=netflix.id))
        await s.commit()

    r = await api.get("/catalog", headers=auth)

    assert r.status_code == 200
    data = r.json()["data"]
    assert [(e["name"], e["selected"]) for e in data] == [
        ("Netflix", True),
        ("Spotify", False),
    ]
    assert {"id", "service_type", "category"} <= data[0].keys()
    assert "aliases" not in data[0]


async def test_saving_replaces_the_list(api, auth, make_entry, user_id, all_rows):
    a = await make_entry("A")
    b = await make_entry("B")
    c = await make_entry("C")
    await api.put(
        "/assumed", headers=auth, json={"catalog_entry_ids": [str(a.id), str(b.id)]}
    )

    r = await api.put("/assumed", headers=auth, json={"catalog_entry_ids": [str(c.id)]})

    assert r.status_code == 200
    assert r.json()["data"]["catalog_entry_ids"] == [str(c.id)]
    assert [row.catalog_entry_id for row in await all_rows(AssumedEntry)] == [c.id]


async def test_unknown_ids_are_ignored_and_duplicates_collapse(
    api, auth, make_entry, all_rows
):
    a = await make_entry("A")
    ids = [str(a.id), str(a.id), str(uuid.uuid4())]

    r = await api.put("/assumed", headers=auth, json={"catalog_entry_ids": ids})

    assert r.status_code == 200
    assert r.json()["data"]["catalog_entry_ids"] == [str(a.id)]
    assert len(await all_rows(AssumedEntry)) == 1


async def test_an_empty_list_clears_it(api, auth, make_entry, all_rows):
    a = await make_entry("A")
    await api.put("/assumed", headers=auth, json={"catalog_entry_ids": [str(a.id)]})
    r = await api.put("/assumed", headers=auth, json={"catalog_entry_ids": []})
    assert r.status_code == 200
    assert await all_rows(AssumedEntry) == []


async def test_saving_never_touches_another_users_list(
    api, auth, make_entry, sessions, other_user_id, all_rows
):
    a = await make_entry("A")
    async with sessions() as s:
        s.add(AssumedEntry(user_id=other_user_id, catalog_entry_id=a.id))
        await s.commit()

    await api.put("/assumed", headers=auth, json={"catalog_entry_ids": []})

    assert len(await all_rows(AssumedEntry)) == 1


async def test_not_a_uuid_is_a_validation_error(api, auth):
    r = await api.put("/assumed", headers=auth, json={"catalog_entry_ids": ["nope"]})
    assert r.status_code == 422
