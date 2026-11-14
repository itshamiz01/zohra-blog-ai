"""
Zohra — Event model.

Represents an underlying real-world occurrence clustered across multiple source documents.
Tracks velocity, momentum, source diversity, confidence, trend scores, and risk flags.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class Event(ZohraBase):
    __tablename__ = "events"

    canonical_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    primary_category: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Technology", index=True
    )
    categories: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)  # multi-label scores

    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", index=True
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now, index=True
    )
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="emerging", index=True
    )  # EventStatus

    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    authority_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)

    velocity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_diversity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, index=True)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    trend_classification: Mapped[str] = mapped_column(
        String(50), nullable=False, default="noise", index=True
    )
    trend_reasons: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    language: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default="en", index=True
    )
    country: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    primary_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    primary_source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    risk_flags: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    high_verification_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    contradiction_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contradictions_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    spam_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_qualified_for_opportunity: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    @property
    def is_qualified_for_part3(self) -> bool:
        return self.is_qualified_for_opportunity

    @is_qualified_for_part3.setter
    def is_qualified_for_part3(self, val: bool) -> None:
        self.is_qualified_for_opportunity = val

    @property
    def contradiction_notes(self) -> list:
        return self.contradictions_json or []

    @contradiction_notes.setter
    def contradiction_notes(self, val: list) -> None:
        self.contradictions_json = val

    merged_into_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_events_status_trend", "status", "trend_score"),
        Index("ix_events_category_status", "primary_category", "status"),
        Index("ix_events_seen_window", "first_seen_at", "last_seen_at"),
    )
