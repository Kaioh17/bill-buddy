import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint("subscription_id", "due_date", "lead_days"),
        Index(
            "reminders_due_idx",
            "remind_at",
            postgresql_where=text("sent_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid()
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    due_date: Mapped[date] = mapped_column(Date)
    lead_days: Mapped[int]
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
