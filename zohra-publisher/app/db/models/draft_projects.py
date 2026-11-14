"""
Zohra — DraftProject model.

Represents an editorial drafting project executing over a Part 4 ResearchPackage.
Tracks lifecycle status, quality scores, grounding scores, versions, and costs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class DraftProjectStatus(str, Enum):
    QUEUED = "queued"
    STRATEGIZING = "strategizing"
    BLUEPRINTING = "blueprinting"
    WRITING = "writing"
    ASSEMBLING = "assembling"
    OPTIMIZING = "optimizing"
    CHECKING = "checking"
    REVISING = "revising"
    READY_FOR_PART6 = "ready_for_part6"
    NEEDS_RESEARCH = "needs_research"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DraftProject(ZohraBase):
    __tablename__ = "draft_projects"

    research_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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

    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="explainer")
    target_audience: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    primary_keyword: Mapped[str] = mapped_column(String(256), nullable=False)
    primary_intent: Mapped[str] = mapped_column(String(64), nullable=False, default="informational")

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    country: Mapped[str] = mapped_column(String(10), nullable=False, default="US")

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DraftProjectStatus.QUEUED.value,
        index=True,
    )

    strategy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    blueprint_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    writer_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0")

    research_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    draft_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grounding_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    readability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    intent_alignment_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    information_gain_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    seo_content_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    brand_voice_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    revalidate_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_dp_status", "status"),
        Index("ix_dp_opp_id", "opportunity_id"),
        Index("ix_dp_research_pkg_id", "research_package_id"),
        Index("ix_dp_site_id", "site_id"),
    )
