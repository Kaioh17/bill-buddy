"""Create all tables (dev only, no migrations yet): uv run python -m db.init_db"""

import asyncio

import app.main  # noqa: F401  (imports every model so Base knows the tables)
from db.database import Base, engine


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # skips existing tables
    await engine.dispose()
    print("tables:", ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    asyncio.run(main())
