import uuid

from sqlalchemy import JSON, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class CatalogEntry(Base):
    """Preseeded service list. It is data, not code (NFR 9)."""

    __tablename__ = "catalog_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, unique=True)
    service_type: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[str]] = mapped_column(JSON, server_default=text("'[]'"))
    merchant_entity_ids: Mapped[list[str]] = mapped_column(
        JSON, server_default=text("'[]'")
    )
