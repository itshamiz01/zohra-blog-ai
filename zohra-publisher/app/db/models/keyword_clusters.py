"""
Zohra — KeywordCluster and KeywordClusterMember models.

Groups semantically and intent-related search queries into targetable clusters.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ZohraBase


class KeywordCluster(ZohraBase):
    __tablename__ = "keyword_clusters"

    canonical_topic: Mapped[str] = mapped_column(String(512), nullable=False)
    primary_keyword: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    primary_intent: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en", index=True)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="global", index=True)

    keyword_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    aggregate_demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    commercial_value_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)

    cluster_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Relationships
    members = relationship(
        "KeywordClusterMember", back_populates="cluster", cascade="all, delete-orphan"
    )
    content_gaps = relationship(
        "ContentGap", back_populates="keyword_cluster", cascade="all, delete-orphan"
    )
    questions = relationship(
        "DiscoveredQuestion", back_populates="keyword_cluster", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_clusters_prim_lang_ctry", "primary_keyword", "language", "country"),
    )


class KeywordClusterMember(ZohraBase):
    __tablename__ = "keyword_cluster_members"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keywords.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Relationships
    cluster = relationship("KeywordCluster", back_populates="members")
    keyword = relationship("Keyword", back_populates="cluster_memberships")

    __table_args__ = (
        Index("ix_cluster_members_pair", "cluster_id", "keyword_id", unique=True),
    )
