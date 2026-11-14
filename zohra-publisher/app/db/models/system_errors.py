"""
system_errors — Persistent error log for diagnostics.
Stack traces stored here, never exposed through API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class SystemError(ZohraBase):
    __tablename__ = "system_errors"

    error_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="error", index=True)

    component: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    operation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Link to the entity that caused the error
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Resolution tracking
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_system_errors_severity_resolved", "severity", "resolved"),
        Index("ix_system_errors_component_created", "component", "created_at"),
    )
