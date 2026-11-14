"""
Zohra — ResearchQuery model.

Targeted search queries generated for research questions and primary-source discovery.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ResearchQuery(ZohraBase):
    __tablename__ = "research_queries"

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

    query: Mapped[str] = mapped_column(String(512), nullable=False)

    # primary_source, official_documentation, general_web, news,
    # research, community, historical, verification, contradiction_resolution
    query_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general_web", index=True
    )

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    country: Mapped[str] = mapped_column(String(10), nullable=False, default="US")

    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)

    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="internal")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_res_query_proj_type", "research_project_id", "query_type"),
        Index("ix_res_query_proj_status", "research_project_id", "status"),
    )
