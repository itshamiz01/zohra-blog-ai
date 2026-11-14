"""
Zohra — DiscoveredQuestion model.

Stores real user questions extracted from SERPs (People Also Ask),
autocomplete, community discussions, or entity relationships.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ZohraBase


class DiscoveredQuestion(ZohraBase):
    __tablename__ = "discovered_questions"

    question: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_question: Mapped[str] = mapped_column(Text, nullable=False)

    intent: Mapped[str] = mapped_column(String(50), nullable=False, default="informational")

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

    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="serp_paa")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Relationships
    keyword_cluster = relationship("KeywordCluster", back_populates="questions")
    opportunity = relationship("ContentOpportunity", back_populates="questions")

    __table_args__ = (
        Index("ix_questions_source_imp", "source", "importance_score"),
    )
