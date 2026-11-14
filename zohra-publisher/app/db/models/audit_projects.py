"""
Zohra — AuditProject model (Part 6).

Primary record tracking the independent editorial and publication quality audit
of an EditorialDraftPackage against its source ResearchPackage and SiteProfile.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class AuditProject(ZohraBase):
    __tablename__ = "audit_projects"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    research_project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    research_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_package_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

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

    audit_type: Mapped[str] = mapped_column(String(32), nullable=False, default="full_publication_audit")
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="LOW", index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Independent Quality Scores (0.0 - 100.0)
    factual_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    citation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grounding_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    temporal_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    originality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    intent_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    information_gain_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    seo_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    content_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    structure_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    brand_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    overall_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Issue Counts
    critical_issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    major_issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minor_issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Final Decision: PASS, REVISE, MORE_RESEARCH, HUMAN_REVIEW, REJECT
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    decision_reason_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    # Cost Tracking
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Versioning & Reproducibility
    auditor_version: Mapped[str] = mapped_column(String(32), nullable=False, default="part6-v1.0")
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="policy-v1.0")
    audit_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_ap_draft_proj", "draft_project_id"),
        Index("ix_ap_res_pkg", "research_package_id"),
        Index("ix_ap_decision", "decision"),
        Index("ix_ap_status", "status"),
    )
