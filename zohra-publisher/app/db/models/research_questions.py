"""
Zohra — ResearchQuestion model.

Decomposed research questions with priority, required evidence rigor, and status tracking.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ResearchQuestion(ZohraBase):
    __tablename__ = "research_questions"

    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question: Mapped[str] = mapped_column(String(1024), nullable=False)

    # definition, technical, pricing, availability, timeline, comparison,
    # limitation, statistics, historical, legal, product, process, risk, user_experience
    question_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # CRITICAL, HIGH, MEDIUM, LOW
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MEDIUM", index=True
    )

    requires_primary_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_multiple_sources: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # unanswered, searching, partially_answered, answered, not_found
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unanswered", index=True
    )

    answer_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_res_q_proj_priority", "research_project_id", "priority"),
        Index("ix_res_q_proj_status", "research_project_id", "status"),
    )
