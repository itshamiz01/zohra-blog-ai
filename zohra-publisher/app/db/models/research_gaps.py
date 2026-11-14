"""
Zohra — ResearchGap model.

Tracks identified holes in evidence (unanswered questions, weak sources,
missing primary sources, regional uncertainty) to drive follow-up research iterations.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ResearchGap(ZohraBase):
    __tablename__ = "research_gaps"

    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_questions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # no_source, weak_source, contradictory, outdated,
    # missing_primary_source, insufficient_corroboration, regional_uncertainty, temporal_uncertainty
    gap_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(20), nullable=False, default="major", index=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)

    # open, investigating, resolved, accepted_unknown
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_res_gap_proj_status", "research_project_id", "status"),
        Index("ix_res_gap_proj_type", "research_project_id", "gap_type"),
    )
