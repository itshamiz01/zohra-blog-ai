"""
Zohra — Contradiction model.

Tracks factual disagreements between claims, severity, and resolution status
(e.g., resolved by primary source, freshness, regional scope, version, or human review).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class Contradiction(ZohraBase):
    __tablename__ = "contradictions"

    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    claim_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # numeric_mismatch, date_mismatch, capability_mismatch, existence_mismatch, attribution_conflict
    contradiction_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="numeric_mismatch", index=True
    )

    # critical, major, minor
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="major", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # unresolved, resolved_by_primary_source, resolved_by_freshness,
    # resolved_by_scope, resolved_by_region, resolved_by_version, requires_human_review
    resolution_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unresolved", index=True
    )
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    preferred_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
    )

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_contra_proj_status", "research_project_id", "resolution_status"),
        Index("ix_contra_proj_severity", "research_project_id", "severity"),
    )
