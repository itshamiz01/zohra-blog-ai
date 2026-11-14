"""
Zohra — SQLAlchemy base model.

All database models inherit from ZohraBase, which provides:
  - UUID primary key
  - created_at / updated_at timestamps (UTC, timezone-aware)
  - __tablename__ auto-generation from class name
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Compatible with PostgreSQL JSONB in production and SQLite JSON in testing
JSON_FIELD = JSONB().with_variant(JSON(), "sqlite")


class ZohraBase(DeclarativeBase):
    """Base class for all Zohra database models."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"
