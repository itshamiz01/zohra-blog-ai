"""
Zohra — ResearchProject model.

Tracks autonomous deep research projects executed for qualified ContentOpportunityPackages.
Maintains state machine transitions, research depth levels, coverage metrics, and costs.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ResearchProject(ZohraBase):
    __tablename__ = "research_projects"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    research_objective: Mapped[str] = mapped_column(Text, nullable=False)

    # LIGHT, STANDARD, DEEP, CRITICAL
    research_depth: Mapped[str] = mapped_column(
        String(50), nullable=False, default="STANDARD", index=True
    )

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    country: Mapped[str] = mapped_column(String(10), nullable=False, default="US", index=True)

    # queued, planning, discovering, collecting, extracting, verifying,
    # synthesizing, quality_review, completed, needs_more_research, blocked, failed, cancelled
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    risk_level: Mapped[str] = mapped_column(
        String(50), nullable=False, default="standard", index=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primary_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claim_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verified_claim_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    critical_claim_coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    research_confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    research_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    research_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stop_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_res_proj_site_status", "site_id", "status"),
        Index("ix_res_proj_opp_version", "opportunity_id", "research_version"),
    )
