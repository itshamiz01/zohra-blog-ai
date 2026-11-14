"""
Zohra — SiteTopic model.

Defines thematic relevance weights and authority proxies for a site.
Relevance weights are normalized 0.0 to 1.0; authority proxies 0.0 to 100.0.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ZohraBase


class SiteTopic(ZohraBase):
    __tablename__ = "site_topics"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_slug: Mapped[str] = mapped_column(String(255), nullable=False)

    # 0.0 to 1.0 topic alignment weight
    relevance_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Observable authority score (0.0 to 100.0) based on coverage & performance
    topical_authority_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)

    historical_post_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    site = relationship("Site", back_populates="topics")

    __table_args__ = (
        Index("ix_site_topics_site_slug", "site_id", "canonical_slug", unique=True),
    )
