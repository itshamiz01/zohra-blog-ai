"""
Zohra — DiscoveryQuery model.

Configurable target search / monitoring queries for continuous web discovery.
Includes approval workflow (candidate, approved, active, paused, rejected)
to prevent unbounded query explosion.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class DiscoveryQuery(ZohraBase):
    __tablename__ = "discovery_queries"

    query: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="en")
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)

    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="approved"
    )  # candidate, approved, active, paused, rejected

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    average_results: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (Index("ix_disc_queries_status_next", "status", "enabled", "next_run_at"),)
