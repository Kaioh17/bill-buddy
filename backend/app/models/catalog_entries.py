import uuid

from sqlalchemy import Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base
class CatalogEntry(Base):
    """Preseeded service list. It is data, not code (NFR 9)."""

    __tablename__ = "catalog_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(Text, unique=True)
    service_type: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    merchant_entity_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'")
    )