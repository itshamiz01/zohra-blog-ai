"""
Zohra — EventDocument model.

Maps source documents to event clusters, recording similarity,
relevance, and provenance flags.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class EventDocument(ZohraBase):
    __tablename__ = "event_documents"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    is_primary_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_original_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("event_id", "document_id", name="uq_event_document"),
        Index("ix_event_doc_composite", "event_id", "document_id"),
    )
