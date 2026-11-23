import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class LinkStatus(enum.StrEnum):
    ACTIVE = "active"
    NEEDS = "needs_reauth"
    DISCONNECTED = "disconnected"


class LinkedAccount(Base):
    """A Plaid item for a user, plus its sync state."""

    __tablename__ = "linked_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plaid_item_id: Mapped[str] = mapped_column(Text)
    institution_name: Mapped[str] = mapped_column(Text)
    access_token_enc: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[LinkStatus] = mapped_column(
        Enum(
            LinkStatus,
            name="link_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        server_default=LinkStatus.ACTIVE.value,
    )
    cursor: Mapped[str | None] = mapped_column(
        Text
    )  # Plaid bookmark, NULL before first import
    history_ready: Mapped[bool] = mapped_column(server_default=text("false"))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    sync_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Failed syncs in a row, drives the retry schedule. Reset to 0 on success.
    sync_failures: Mapped[int] = mapped_column(Integer, server_default="0")

    yearly_check_status: Mapped[str | None] = mapped_column(String(32))
    yearly_check_attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    yearly_check_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
