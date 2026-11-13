import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class MatchedPayment(Base):
    """A transaction that belongs to a subscription."""

    __tablename__ = "matched_payments"
    __table_args__ = (
        Index("matched_payments_user_date_idx", "user_id", "date"),
        Index("matched_payments_sub_idx", "subscription_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid()
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    transaction_id: Mapped[str] = mapped_column(Text, unique=True)  # no FK on purpose
    date: Mapped[dt.date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    merchant_name: Mapped[str] = mapped_column(Text)
