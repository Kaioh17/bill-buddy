from fastapi import FastAPI

from app.models import (  # noqa: F401  (registers tables on Base.metadata)
    assumed_entries,
    catalog_entries,
    linked_accounts,
    merchnant_links,
    reminders,
    subscriptions,
    transactions,
    users,
)
from app.routers import health
from db.database import Base, engine, get_db  # noqa: F401

app = FastAPI(title="Bill Buddy API")
app.include_router(health.router)
