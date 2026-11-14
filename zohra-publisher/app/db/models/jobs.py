"""
jobs — General-purpose background job queue.
Designed for idempotent processing with locking, retries, and dead-letter support.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class Job(ZohraBase):
    __tablename__ = "jobs"

    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    payload: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    # Scheduling
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Retry tracking
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Distributed locking — prevent two workers from processing the same job
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Error details for failed jobs
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Idempotency key — prevents duplicate job creation
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)

    __table_args__ = (
        Index("ix_jobs_status_priority", "status", "priority"),
        Index("ix_jobs_status_scheduled", "status", "scheduled_for"),
        Index("ix_jobs_type_status", "job_type", "status"),
    )
