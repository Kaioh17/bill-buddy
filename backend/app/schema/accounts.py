"""Response schemas for the /accounts routes. The token and cursor are never exposed."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.linked_accounts import LinkStatus
from app.schema.general import ORMModel


class AccountOut(ORMModel):
    id: uuid.UUID
    institution_name: str
    status: LinkStatus  # "needs_reauth" means the user must reconnect
    history_ready: bool
    last_sync_at: datetime | None
    next_sync: datetime | None
    last_error: str | None  # a Plaid error code such as RATE_LIMIT_EXCEEDED
    created_at: datetime


class SyncOut(BaseModel):
    last_sync_at: datetime | None
    added: int
    modified: int
    removed: int
