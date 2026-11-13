import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class MerchantLink(Base):
    """Remembers that this merchant is that catalog service"""

    __tablename__ = "merchant_links"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    merchant_key: Mapped[str] = mapped_column(Text, primary_key=True)
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catalog_entries.id"))
