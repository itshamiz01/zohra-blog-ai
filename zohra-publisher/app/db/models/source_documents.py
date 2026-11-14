"""
Zohra — SourceDocument model.

Normalized standard representation of every fetched item from external sources.
Tracks provenance, content hashes, deduplication pointers, and sanitization status.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class SourceDocument(ZohraBase):
    __tablename__ = "source_documents"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    external_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    language: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    language_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    simhash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="rss")
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetch_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="fetched", index=True
    )
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    spam_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_exact_duplicate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    is_near_duplicate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_source_docs_source_external", "source_id", "external_id"),
        Index("ix_source_docs_source_published", "source_id", "published_at"),
    )
