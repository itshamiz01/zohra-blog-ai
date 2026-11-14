"""
Zohra — PublicationJob & PublicationSchedule models (Part 7).

Manages end-to-end publication lifecycle, state machine transitions, scheduling,
post verification, idempotency keys, and reconciliation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class PublicationJob(ZohraBase):
    __tablename__ = "publication_jobs"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    draft_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    authorization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_authorizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    publication_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    # publication_mode: DRAFT, SCHEDULE, PUBLISH_NOW

    desired_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    # desired_status: draft, future, publish

    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    wordpress_post_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    wordpress_post_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CREATED", index=True)
    # State machine: CREATED, VALIDATING, MEDIA_PREPARING, MEDIA_READY, LINKS_RESOLVING,
    # SEO_PACKAGING, RENDERING, PREVIEW_READY, SCHEDULED_FOR_PUBLICATION, PUBLISHING,
    # VERIFYING, PUBLISHED, INDEXING_HANDOFF, COMPLETED, BLOCKED, FAILED, RECONCILIATION_REQUIRED, CANCELLED

    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    preview_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    rendered_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    schedules = relationship("PublicationSchedule", back_populates="job", cascade="all, delete-orphan")
    events = relationship("PublicationEvent", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_pub_job_site_status", "site_id", "status"),
        Index("ix_pub_job_article", "article_id"),
    )


class PublicationSchedule(ZohraBase):
    __tablename__ = "publication_schedules"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    publication_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    scheduled_local_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    scheduled_utc_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)

    job = relationship("PublicationJob", back_populates="schedules")

    __table_args__ = (
        Index("ix_pub_sched_time", "scheduled_utc_time", "status"),
    )


class PublicationEvent(ZohraBase):
    __tablename__ = "publication_events"

    publication_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_state: Mapped[str] = mapped_column(String(64), nullable=False)

    wordpress_post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    job = relationship("PublicationJob", back_populates="events")

    __table_args__ = (
        Index("ix_pub_events_job_type", "publication_job_id", "event_type"),
    )
