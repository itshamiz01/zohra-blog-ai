"""
Zohra — PublicationApprovals, PublishedArticles, and IndexingJobs models (Part 7).

Manages manual admin approval gates, the final published article registry with
lineage mapping, and the indexing handoff records for Part 8.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class PublicationApproval(ZohraBase):
    __tablename__ = "publication_approvals"

    publication_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # APPROVE, REJECT, REQUEST_CHANGES
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    __table_args__ = (
        Index("ix_pub_approval_job", "publication_job_id"),
    )


class PublishedArticle(ZohraBase):
    __tablename__ = "published_articles"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
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
    publication_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    wordpress_post_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    slug: Mapped[str] = mapped_column(String(512), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    featured_media_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_ids: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    tag_ids: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)

    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="VERIFIED", index=True)
    verification_details_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    package_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False)

    __table_args__ = (
        Index("ix_pub_art_site_slug", "site_id", "slug"),
        Index("ix_pub_art_wp_id", "site_id", "wordpress_post_id", unique=True),
    )


class IndexingJob(ZohraBase):
    __tablename__ = "indexing_jobs"

    publication_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    published_article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("published_articles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED", index=True)
    search_console_property: Mapped[str | None] = mapped_column(String(512), nullable=True)

    first_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sitemap_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_indexing_job_site_status", "site_id", "status"),
    )
