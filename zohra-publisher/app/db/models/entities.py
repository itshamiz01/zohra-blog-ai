"""
Zohra — Entity and DocumentEntity models.

Maintains canonical entities (Person, Org, Product, Tech, Location, etc.)
and document-entity associations with mention counts and confidence.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class Entity(ZohraBase):
    __tablename__ = "entities"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # EntityType
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    aliases: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)  # list[str]
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)


class DocumentEntity(ZohraBase):
    __tablename__ = "document_entities"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    mentions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("document_id", "entity_id", name="uq_doc_entity"),
        Index("ix_doc_entity_composite", "document_id", "entity_id"),
    )
