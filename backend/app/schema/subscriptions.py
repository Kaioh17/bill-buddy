"""Response schema for /subscriptions. Money is a Decimal, sent as a string."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from app.models.subscriptions import Frequency, SubscriptionKind
from app.schema.general import ORMModel


class SubscriptionOut(ORMModel):
    id: uuid.UUID
    name: str
    label: Literal["actual", "likely", "manual"]
    frequency: Frequency
    kind: SubscriptionKind
    category: str | None
    service_type: str | None
    amount: Decimal
    last_payment_date: date | None
    next_expected_date: date
    likely_reasons: list[str]  # why it is only likely, empty otherwise
    on_assumed_list: bool
    similar_to: list[
        str
    ]  # names of other active subscriptions of the same service type
