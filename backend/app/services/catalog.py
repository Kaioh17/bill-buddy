"""The preseeded service catalog, the user's assumed list, and merchant matching."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assumed_entries import AssumedEntry
from app.models.catalog_entries import CatalogEntry
from app.schema.catalog import CatalogEntryOut


def matches(entry: CatalogEntry, entity_id: str | None, *names: str | None) -> bool:
    """Does this bank merchant belong to this catalog service? Plaid's stable merchant
    id first, then a specific alias anywhere in the name."""
    if entity_id and entity_id in entry.merchant_entity_ids:
        return True
    text = " ".join(n.lower() for n in names if n)
    return any(alias.lower() in text for alias in entry.aliases)


def find_entry(
    entries: list[CatalogEntry], entity_id: str | None, *names: str | None
) -> CatalogEntry | None:
    """An entity id match beats an alias match, so a wrong alias can't steal it."""
    for entry in entries:
        if entity_id and entity_id in entry.merchant_entity_ids:
            return entry
    return next((e for e in entries if matches(e, None, *names)), None)


async def all_entries(db: AsyncSession) -> list[CatalogEntry]:
    return list(await db.scalars(select(CatalogEntry).order_by(CatalogEntry.name)))


async def assumed_ids(db: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    return set(
        await db.scalars(
            select(AssumedEntry.catalog_entry_id).where(AssumedEntry.user_id == user_id)
        )
    )


async def list_catalog(db: AsyncSession, user_id: uuid.UUID) -> list[CatalogEntryOut]:
    chosen = await assumed_ids(db, user_id)
    return [
        CatalogEntryOut(
            id=e.id,
            name=e.name,
            service_type=e.service_type,
            category=e.category,
            selected=e.id in chosen,
        )
        for e in await all_entries(db)
    ]


async def save_assumed(
    db: AsyncSession, user_id: uuid.UUID, ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    """Replace the list. Ids not in the catalog are dropped, not an error (TC-07)."""
    valid = list(
        await db.scalars(select(CatalogEntry.id).where(CatalogEntry.id.in_(set(ids))))
    )
    await db.execute(delete(AssumedEntry).where(AssumedEntry.user_id == user_id))
    db.add_all(AssumedEntry(user_id=user_id, catalog_entry_id=i) for i in valid)
    await db.commit()
    return valid
