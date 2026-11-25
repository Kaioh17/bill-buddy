"""The preseeded catalog is data (NFR 9): about 20 services, some sharing a type."""

from collections import Counter

import pytest

from app.models.catalog_entries import CatalogEntry
from db.seed_catalog import ENTRIES, seed

pytestmark = pytest.mark.anyio


def test_the_list_is_about_twenty_services_with_shared_types():
    assert len(ENTRIES) >= 20
    assert len({e["name"] for e in ENTRIES}) == len(ENTRIES)
    assert any(n >= 2 for n in Counter(e["service_type"] for e in ENTRIES).values())


def test_aliases_are_specific_lowercase_names():
    for e in ENTRIES:
        assert e["aliases"], e["name"]
        assert all(a == a.lower() and len(a) > 3 for a in e["aliases"]), e["name"]


async def test_seeding_twice_adds_nothing_the_second_time(session, all_rows):
    await seed(session)
    await seed(session)
    assert len(await all_rows(CatalogEntry)) == len(ENTRIES)
