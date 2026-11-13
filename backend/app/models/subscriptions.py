import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class SubscriptionSource(enum.StrEnum):
    DETECTED = "DETECTED"
    MANUAL = "MANUAL"


class Frequency(enum.StrEnum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class SubscriptionKind(enum.StrEnum):
    SUBSCRIPTION = "SUBSCRIPTION"
    BILL = "BILL"


class SubscriptionStatus(enum.StrEnum):
    ACTUAL = "ACTUAL"
    LIKELY = "LIKELY"


def _text_enum(cls: type[enum.Enum], name: str) -> Enum:
    """Text column with a CHECK constraint, not a native Postgres ENUM."""
    return Enum(cls, name=name, native_enum=False, create_constraint=True)


class Subscription(Base):
    """Detected and manual subscriptions, in one table."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="subscriptions_amount_positive"),
        CheckConstraint(
            "(source = 'MANUAL' AND merchant_key IS NULL AND status IS NULL) OR "
            "(source = 'DETECTED' AND merchant_key IS NOT NULL AND status IS NOT NULL)",
            name="subscriptions_source_fields",
        ),
        Index("subscriptions_user_idx", "user_id", "is_active"),
        Index("subscriptions_match_idx", "user_id", "merchant_key", "frequency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    source: Mapped[SubscriptionSource] = mapped_column(
        _text_enum(SubscriptionSource, "subscription_source")
    )
    merchant_key: Mapped[str | None] = mapped_column(Text)  # NULL for manual
    name: Mapped[str] = mapped_column(Text)
    frequency: Mapped[Frequency] = mapped_column(_text_enum(Frequency, "subscription_frequency"))
    kind: Mapped[SubscriptionKind] = mapped_column(
        _text_enum(SubscriptionKind, "subscription_kind"),
        server_default=SubscriptionKind.SUBSCRIPTION.value,
    )
    service_type: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SubscriptionStatus | None] = mapped_column(
        _text_enum(SubscriptionStatus, "subscription_status")
    )  # NULL for manual
    likely_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    last_payment_date: Mapped[date | None] = mapped_column(Date)
    next_expected_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DismissedSubscription(Base):
    """A rejected detection. It must not come back."""

    __tablename__ = "dismissed_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    merchant_key: Mapped[str] = mapped_column(Text, primary_key=True)
    frequency: Mapped[Frequency] = mapped_column(
        _text_enum(Frequency, "dismissed_frequency"), primary_key=True
    )
