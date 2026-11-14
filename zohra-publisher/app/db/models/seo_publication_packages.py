"""
Zohra — SEOPublicationPackage model (Part 7).

Stores final implementation-level SEO metadata, canonical URLs, robots directives,
Open Graph, Twitter card elements, and structured JSON-LD schemas.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class SEOPublicationPackage(ZohraBase):
    __tablename__ = "seo_publication_packages"

    publication_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    meta_title: Mapped[str] = mapped_column(String(512), nullable=False)
    meta_description: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    primary_topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)

    robots_directive: Mapped[str] = mapped_column(String(64), nullable=False, default="index,follow")
    schema_types: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    schema_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    open_graph_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    open_graph_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    open_graph_image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    twitter_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    twitter_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    twitter_image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    __table_args__ = (
        Index("ix_seo_pkg_slug", "site_id", "slug"),
    )
