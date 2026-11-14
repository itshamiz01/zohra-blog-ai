"""
Zohra — Source model.

Centralized source registry representing external publishing channels,
RSS/Atom feeds, search engines, official portals, and community discussions.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class Source(ZohraBase):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="rss", index=True)

    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default="en", index=True
    )

    tier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, index=True
    )  # SourceTier 1-5

    authority_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    signal_value_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)

    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    polling_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    is_trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_authentication: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    robots_policy_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    health_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="healthy", index=True
    )
    circuit_breaker_state: Mapped[str] = mapped_column(String(20), nullable=False, default="closed")
    circuit_breaker_tripped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    @property
    def circuit_state(self) -> str:
        return self.circuit_breaker_state

    @circuit_state.setter
    def circuit_state(self, val: str) -> None:
        self.circuit_breaker_state = val

    __table_args__ = (
        Index("ix_sources_enabled_priority", "is_enabled", "priority"),
        Index("ix_sources_health_checked", "health_status", "last_checked_at"),
    )
