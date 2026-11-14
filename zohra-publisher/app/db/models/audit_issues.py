"""
Zohra — AuditIssue model (Part 6).

Detailed record of a specific issue found during editorial, factual,
citation, SEO, originality, or risk verification passes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class AuditIssue(ZohraBase):
    __tablename__ = "audit_issues"

    audit_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    issue_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    issue_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # CRITICAL, MAJOR, MODERATE, MINOR, INFO
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MAJOR", index=True)

    # Precise Content Location
    section_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paragraph_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cross-reference
    claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)

    # Routing target: Part 5 (writer), Part 4 (research), human, or reject
    routing_target: Mapped[str] = mapped_column(String(32), nullable=False, default="part5_writer")

    # Status: open, resolved, overridden
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_ai_proj_sev", "audit_project_id", "severity"),
        Index("ix_ai_code", "issue_code"),
    )
