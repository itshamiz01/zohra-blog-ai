"""
Zohra — Keyword model.

Represents an individual search query, its normalized form, classified intent,
internal search demand score, and provenance-tracked external metrics.

CRITICAL PRINCIPLE:
If exact search volume or CPC is unavailable, store NULL.
Never fabricate search metrics or convert missing values to 0.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class Keyword(ZohraBase):
    __tablename__ = "keywords"

    keyword: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_keyword: Mapped[str] = mapped_column(String(512), nullable=False, index=True)

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="global", index=True)

    intent: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # SearchIntent
    intent_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    secondary_intent: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Internal 0-100 score synthesizing relative demand signals
    search_demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, index=True)

    # External metrics with strict provenance. NULL if not verified from an actual provider
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_volume_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    search_volume_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    competition_metric: Mapped[float | None] = mapped_column(Float, nullable=True)
    competition_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpc_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cpc_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    trend_direction: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown"
    )  # rising, stable, falling, unknown
    freshness_sensitivity: Mapped[str] = mapped_column(
        String(50), nullable=False, default="evergreen"
    )  # FreshnessDecayType

    commercial_value_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    # Relationships
    cluster_memberships = relationship(
        "KeywordClusterMember", back_populates="keyword", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_keywords_norm_lang_ctry", "normalized_keyword", "language", "country", unique=True),
        Index("ix_keywords_intent_demand", "intent", "search_demand_score"),
    )
