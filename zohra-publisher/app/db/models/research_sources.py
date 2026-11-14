"""
Zohra — ResearchSource model.

Sources evaluated during deep research with tiering, primary source classification,
independence groups (to stop copied PRs counting as independent corroboration), and provenance.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ResearchSource(ZohraBase):
    __tablename__ = "research_sources"

    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)

    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    updated_at_source: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    source_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # official_documentation, official_announcement, academic_paper, regulatory_filing,
    # news_report, industry_blog, community_forum, review
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="news_report", index=True
    )

    is_primary_source: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    is_official_source: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    # Identifies shared underlying PR or syndicated network
    independence_group_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )

    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    authority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    research_value_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # discovered, fetched, parsed, rejected, processed
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="discovered", index=True
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_res_src_proj_canonical", "research_project_id", "canonical_url"),
        Index("ix_res_src_proj_primary", "research_project_id", "is_primary_source"),
    )
