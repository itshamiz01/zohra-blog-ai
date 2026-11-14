"""
Zohra — SiteContent model.

Index of existing website articles used for cannibalization detection,
internal gap analysis, and content action recommendation (CREATE vs UPDATE vs EXPAND).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class SiteContent(ZohraBase):
    __tablename__ = "site_content"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    slug: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    primary_topic: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    primary_keyword: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    secondary_keywords: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)
    primary_intent: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="global")

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="published", index=True)

    embedding: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    performance_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    # Relationships
    site = relationship("Site", back_populates="content_items")

    __table_args__ = (
        Index("ix_site_content_site_url", "site_id", "url", unique=True),
        Index("ix_site_content_site_topic", "site_id", "primary_topic"),
        Index("ix_site_content_site_keyword", "site_id", "primary_keyword"),
    )
