"""
Zohra — AuditCheck model (Part 6).

Tracks completion, status, and score of individual verification checks
(e.g., claim audit, citation audit, numeric audit, SEO, risk, adversarial).
Ensures no article passes if any required check failed or errored.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class AuditCheck(ZohraBase):
    __tablename__ = "audit_checks"

    audit_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    check_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # PENDING, RUNNING, PASS, FAIL, ERROR, SKIPPED
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)

    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_ac_proj_type", "audit_project_id", "check_type", unique=True),
    )
