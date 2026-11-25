"""Response schema for /reconciliation (FR 3b: name, last payment date, amount)."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class UnexpectedOut(BaseModel):
    """Found in the bank data, not on the assumed list."""

    subscription_id: uuid.UUID
    name: str
    last_payment_date: date | None
    amount: Decimal


class UnconfirmedOut(BaseModel):
    """On the assumed list, no matching bank payment in the last 60 days."""

    catalog_entry_id: uuid.UUID
    name: str
    last_payment_date: date | None  # None: no payment found at all
    amount: Decimal | None


class ReconciliationOut(BaseModel):
    unexpected: list[UnexpectedOut]
    unconfirmed: list[UnconfirmedOut]
