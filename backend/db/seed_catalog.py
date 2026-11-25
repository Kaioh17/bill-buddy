"""Seed the catalog of known services (NFR 9, it is data, not code).

    uv run python -m db.seed_catalog      (also run by db.init_db)

Safe to run again: services are matched by name, new ones are added, existing rows are
left as they are so hand edits survive. Aliases are specific, "apple music" and not
"apple", because an alias matches anywhere in a merchant name.
Plaid merchant entity ids are not listed: add them to `merchant_entity_ids` once real
ids are known, an id match is checked before any alias.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog_entries import CatalogEntry

# name, service_type, category, aliases
_ROWS: list[tuple[str, str, str, list[str]]] = [
    ("Netflix", "Video streaming", "Entertainment", ["netflix"]),
    ("Hulu", "Video streaming", "Entertainment", ["hulu"]),
    (
        "Disney+",
        "Video streaming",
        "Entertainment",
        ["disney plus", "disneyplus", "disney+"],
    ),
    ("Max", "Video streaming", "Entertainment", ["hbo max", "hbomax"]),
    ("Apple TV+", "Video streaming", "Entertainment", ["apple tv"]),
    (
        "Prime Video",
        "Video streaming",
        "Entertainment",
        ["prime video", "amazon prime video"],
    ),
    ("Spotify", "Music streaming", "Entertainment", ["spotify"]),
    ("Apple Music", "Music streaming", "Entertainment", ["apple music"]),
    (
        "YouTube Premium",
        "Music streaming",
        "Entertainment",
        ["youtube premium", "youtubepremium"],
    ),
    ("Audible", "Audiobooks", "Entertainment", ["audible"]),
    ("PlayStation Plus", "Gaming", "Entertainment", ["playstation plus", "ps plus"]),
    ("Xbox Game Pass", "Gaming", "Entertainment", ["xbox game pass", "game pass"]),
    ("iCloud+", "Cloud storage", "Productivity", ["icloud"]),
    ("Google One", "Cloud storage", "Productivity", ["google one"]),
    ("Dropbox", "Cloud storage", "Productivity", ["dropbox"]),
    (
        "Microsoft 365",
        "Office software",
        "Productivity",
        ["microsoft 365", "office 365"],
    ),
    ("Adobe Creative Cloud", "Design software", "Productivity", ["adobe"]),
    ("Notion", "Notes and planning", "Productivity", ["notion labs", "notion.so"]),
    ("Planet Fitness", "Gym", "Health & fitness", ["planet fitness"]),
    ("Peloton", "Gym", "Health & fitness", ["peloton"]),
    ("The New York Times", "News", "News", ["nytimes", "new york times"]),
    (
        "Amazon Prime",
        "Shopping membership",
        "Shopping",
        ["amazon prime", "prime membership"],
    ),
]

ENTRIES = [
    {
        "name": n,
        "service_type": t,
        "category": c,
        "aliases": a,
        "merchant_entity_ids": [],
    }
    for n, t, c, a in _ROWS
]


async def seed(db: AsyncSession) -> None:
    have = set(await db.scalars(select(CatalogEntry.name)))
    db.add_all(CatalogEntry(**e) for e in ENTRIES if e["name"] not in have)
    await db.commit()


async def main() -> None:
    from db.database import SessionLocal, engine

    async with SessionLocal() as db:
        await seed(db)
    await engine.dispose()
    print(f"catalog: {len(ENTRIES)} services seeded")


if __name__ == "__main__":
    asyncio.run(main())
