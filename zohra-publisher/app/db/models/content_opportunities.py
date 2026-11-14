"""
Zohra — ContentOpportunity model.

Core entity produced by Part 3 (Content Opportunity Intelligence Engine).
Represents a vetted, scored, intent-aligned topic angle for publication.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class ContentOpportunity(ZohraBase):
    __tablename__ = "content_opportunities"

    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topic_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    canonical_topic: Mapped[str] = mapped_column(String(512), nullable=False)
    proposed_angle: Mapped[str] = mapped_column(String(512), nullable=False)
    working_title: Mapped[str] = mapped_column(String(1024), nullable=False)

    primary_keyword: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    primary_intent: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    secondary_intent: Mapped[str | None] = mapped_column(String(50), nullable=True)

    content_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # ContentType
    target_audience: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="global", index=True)

    cluster_role: Mapped[str] = mapped_column(String(50), nullable=False, default="standalone")  # ClusterRole
    recommended_action: Mapped[str] = mapped_column(
        String(50), nullable=False, default="create", index=True
    )  # ContentAction: create, update, expand, merge, watch, reject, review
    target_content_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("site_content.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Detailed Dimension Scores (0.0 to 100.0)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    search_demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    intent_strength_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    competition_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)  # 0=weak, 100=strong
    competition_opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    evergreen_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    site_relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, index=True)
    topical_authority_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    original_value_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    information_gain_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    serp_gap_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    monetization_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    audience_fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    content_type_fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    cannibalization_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Overall Synthesized Scores
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, index=True)

    # Audit & Scoring Diagnostics
    scoring_profile: Mapped[str] = mapped_column(String(50), nullable=False, default="default")
    score_breakdown: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    penalties_breakdown: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    score_reasons: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)

    # Status, Priority & Execution Gating
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="candidate", index=True)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="qualified", index=True)
    dependency_status: Mapped[str] = mapped_column(String(50), nullable=False, default="ready", index=True)

    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_flags: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)

    freshness_decay_type: Mapped[str] = mapped_column(String(50), nullable=False, default="evergreen")
    opportunity_half_life_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    scoring_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    analysis_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    analysis_depth: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")

    # Relationships
    site = relationship("Site", back_populates="opportunities")
    topic_cluster = relationship("TopicCluster", back_populates="opportunities")
    gaps = relationship("ContentGap", back_populates="opportunity", cascade="all, delete-orphan")
    questions = relationship("DiscoveredQuestion", back_populates="opportunity", cascade="all, delete-orphan")
    snapshots = relationship("OpportunitySnapshot", back_populates="opportunity", cascade="all, delete-orphan")
    watchlist_entries = relationship("OpportunityWatchlist", back_populates="opportunity", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_opportunities_site_status_score", "site_id", "status", "opportunity_score"),
        Index("ix_opportunities_event_site", "event_id", "site_id"),
        Index("ix_opportunities_primary_kw", "primary_keyword"),
        Index("ix_opportunities_expires_at", "expires_at"),
    )
