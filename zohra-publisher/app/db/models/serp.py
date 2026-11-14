"""
Zohra — SERPSnapshot and SERPResult models.

Stores point-in-time SERP extractions with position, domain analysis,
detected features (featured snippets, video, forum), and retention control.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class SERPSnapshot(ZohraBase):
    __tablename__ = "serp_snapshots"

    query: Mapped[str] = mapped_column(String(512), nullable=False)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(100), nullable=False, default="mock")
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="global", index=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    device: Mapped[str] = mapped_column(String(20), nullable=False, default="desktop")

    total_results_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)

    features: Mapped[dict | None] = mapped_column(
        JSON_FIELD, nullable=True, default=dict
    )  # featured_snippet, video, forum, news, paa, etc.

    dominant_intent: Mapped[str] = mapped_column(String(50), nullable=False, default="informational")
    intent_alignment_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    results = relationship(
        "SERPResult", back_populates="snapshot", cascade="all, delete-orphan", order_by="SERPResult.position"
    )

    __table_args__ = (
        Index("ix_serp_snapshots_lookup", "query_hash", "country", "language", "device"),
    )


class SERPResult(ZohraBase):
    __tablename__ = "serp_results"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("serp_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    result_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="organic"
    )  # SERPResultType

    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_official_domain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_forum: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    features: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    # Relationships
    snapshot = relationship("SERPSnapshot", back_populates="results")

    __table_args__ = (
        Index("ix_serp_results_snapshot_pos", "snapshot_id", "position"),
        Index("ix_serp_results_domain_pos", "domain", "position"),
    )
