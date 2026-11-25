"""Schemas for /catalog and /assumed."""

import uuid

from pydantic import BaseModel

from app.schema.general import ORMModel


class CatalogEntryOut(ORMModel):
    id: uuid.UUID
    name: str
    service_type: str
    category: str
    selected: bool  # on this user's assumed list


class AssumedIn(BaseModel):
    catalog_entry_ids: list[uuid.UUID]


class AssumedOut(BaseModel):
    catalog_entry_ids: list[uuid.UUID]  # what was actually saved
