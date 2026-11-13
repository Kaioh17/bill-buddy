import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class AssumedEntry(Base):
    """A catalog service that the user says they pay for"""

    __tablename__ = "assumed_entries"

    user_id: Mapped[uuid.UUID] = mapped_column( ForeignKey("users.id", ondelete="CASCADE"), primary_key=True )
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_entries.id"), primary_key=True)