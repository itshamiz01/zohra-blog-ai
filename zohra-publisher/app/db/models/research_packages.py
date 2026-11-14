"""
Zohra — ResearchPackage model.

Immutable, versioned handoff artifacts containing verified facts, uncertain claims,
safe claim IDs, writer policies, and full evidence provenance for Part 5.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ResearchPackage(ZohraBase):
    __tablename__ = "research_packages"

    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    is_immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    research_objective: Mapped[str] = mapped_column(Text, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)

    verified_facts_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    uncertain_claims_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    contradictions_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    timeline_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    entities_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    primary_sources_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    supporting_sources_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    questions_answered_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    questions_unanswered_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    content_gaps_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    important_numbers_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    important_dates_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    limitations_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    risk_flags_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    research_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    research_confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    critical_claim_coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Safe claim IDs, attribution required, do not state as fact
    instructions_for_writer_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)
    citation_map_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_res_pkg_opp_ver", "opportunity_id", "version", unique=True),
        Index("ix_res_pkg_proj_ver", "research_project_id", "version"),
    )
