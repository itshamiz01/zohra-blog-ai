"""
Zohra — ContentGap model.

Represents specific structural dimensions under-covered in existing top SERP pages
(e.g., missing pricing, lack of workflow, unaddressed limitations, regional nuances).

CORE DIRECTIVE:
Word count padding is NOT a content gap. Gaps require observable evidence
of unanswered questions or missing decision dimensions.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class ContentGap(ZohraBase):
    __tablename__ = "content_gaps"

    keyword_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    gap_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # missing_pricing, lack_of_workflow, no_limitations, regional_gap, outdated_competitor, weak_comparisons
    description: Mapped[str] = mapped_column(Text, nullable=False)

    evidence: Mapped[dict | None] = mapped_column(
        JSON_FIELD, nullable=True, default=dict
    )  # e.g. {"analyzed_urls": [...], "missing_aspects": [...]}

    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    keyword_cluster = relationship("KeywordCluster", back_populates="content_gaps")
    opportunity = relationship("ContentOpportunity", back_populates="gaps")

    __table_args__ = (
        Index("ix_content_gaps_type_imp", "gap_type", "importance_score"),
    )
