import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class Transaction(Base):
    """A bank transaction stored as Plaid sends it."""

    __tablename__ = "transactions"
    __table_args__ = (Index("transactions_user_date_idx", "user_id", "date"),)

    transaction_id: Mapped[str] = mapped_column(
        Text, primary_key=True
    )  # Plaid's id, dedupes syncs
    linked_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("linked_accounts.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    plaid_account_id: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    iso_currency_code: Mapped[str | None] = mapped_column(Text)
    date: Mapped[dt.date] = mapped_column(Date)
    authorized_date: Mapped[dt.date | None] = mapped_column(Date)
    pending: Mapped[bool]
    merchant_name: Mapped[str | None] = mapped_column(Text)
    merchant_entity_id: Mapped[str | None] = mapped_column(Text)
    original_description: Mapped[str | None] = mapped_column(Text)
    pfc_primary: Mapped[str | None] = mapped_column(Text)
    pfc_detailed: Mapped[str | None] = mapped_column(Text)
