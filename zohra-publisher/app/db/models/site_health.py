"""
Zohra — SiteHealth & OrphanMedia models (Part 7).

Monages site connection monitoring, circuit breaker state, and orphan media cleanup.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class SiteHealth(ZohraBase):
    __tablename__ = "site_health"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    api_status: Mapped[str] = mapped_column(String(32), nullable=False, default="HEALTHY")
    auth_status: Mapped[str] = mapped_column(String(32), nullable=False, default="VALID")
    media_status: Mapped[str] = mapped_column(String(32), nullable=False, default="HEALTHY")

    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    circuit_state: Mapped[str] = mapped_column(String(32), nullable=False, default="CLOSED")
    # circuit_state: CLOSED, OPEN, HALF_OPEN

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrphanMediaRecord(ZohraBase):
    __tablename__ = "orphan_media_records"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wordpress_media_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_CLEANUP", index=True)
    # status: PENDING_CLEANUP, RETAINED, DELETED

    cleaned_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
