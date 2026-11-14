"""
Zohra — TopicCluster model.

Represents a pillar-and-cluster structural topic network for site architecture.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ZohraBase


class TopicCluster(ZohraBase):
    __tablename__ = "topic_clusters"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    pillar_opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="global")

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)

    aggregate_opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    topical_relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)

    # Relationships
    site = relationship("Site", back_populates="topic_clusters")
    opportunities = relationship("ContentOpportunity", back_populates="topic_cluster")

    __table_args__ = (
        Index("ix_topic_clusters_site_topic", "site_id", "canonical_topic"),
    )
