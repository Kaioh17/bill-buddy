from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum 
from db.database import Base
import uuid

class LinkStatus(enum.StrEnum): 
    ACTIVE = "active"
    NEEDS = "needs_reauth"
    DISCONNECTED= "disconnected"
# linked accounts associated with the item (from plaid)
class LinkedAccount(Base):
    __tablename__ = "linked account"
    id: mapped_column[uuid.UUID] = mapped_column(primary_key=True)
    user_id: mapped_column[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plaid_item_id: mapped_column[str] = mapped_column()
    institution_name: mapped_column[str] = mapped_column()
    access_token_enc: mapped_column[bytearray] = mapped_column() # might remove 
    status: mapped_column[LinkStatus] = mapped_column(Enum(LinkStatus, name ="link_status", 
                                                    values_callable=lambda e: [m.value for m in e]), server_default=LinkStatus.ACTIVE.value)
    cursor: mapped_column[str] = mapped_column(nullable=False)# the plaid bookmark
    history_ready: mapped_column[bool] = mapped_column(nullable=False, server_default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    sync_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    yearly_check_status: Mapped[str | None] = mapped_column(String(32))
    yearly_check_attempts: Mapped[int] = mapped_column(
        Integer, server_default="0"
    )
    yearly_check_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


    
