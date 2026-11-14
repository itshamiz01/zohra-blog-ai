"""
Zohra — OpportunitySnapshot and OpportunityWatchlist models.

OpportunitySnapshot records temporal score evolution for audit, ML feedback, and reevaluation.
OpportunityWatchlist manages opportunities deferred for developing evidence or official confirmation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class OpportunitySnapshot(ZohraBase):
    __tablename__ = "opportunity_snapshots"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    opportunity_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    search_demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    competition_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    evergreen_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    monetization_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cannibalization_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    snapshot_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    # Relationships
    opportunity = relationship("ContentOpportunity", back_populates="snapshots")

    __table_args__ = (
        Index("ix_opp_snapshots_opp_time", "opportunity_id", "recorded_at"),
    )


class OpportunityWatchlist(ZohraBase):
    __tablename__ = "opportunity_watchlist"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    recheck_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    recheck_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Relationships
    opportunity = relationship("ContentOpportunity", back_populates="watchlist_entries")

    __table_args__ = (
        Index("ix_opp_watchlist_active_recheck", "is_active", "recheck_after"),
    )
