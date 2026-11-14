"""
Zohra — Database Models for Article Featured Media & Brand Image Profiles.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class ArticleFeaturedMedia(ZohraBase):
    __tablename__ = "article_featured_media"

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
    publication_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="openai")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="dall-e-3")
    generation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    revised_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_concept_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    validation_details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    local_storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    public_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    wordpress_media_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    wordpress_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/webp")
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=1536)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=864)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    alt_text: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    responsive_variants_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON_FIELD, nullable=True, default=list)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    provenance_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    __table_args__ = (
        Index("ix_afm_site_article", "site_id", "article_id"),
        Index("ix_afm_content_hash", "content_hash"),
        Index("ix_afm_wp_media_id", "wordpress_media_id"),
    )


class ArticleImageBrandProfile(ZohraBase):
    __tablename__ = "article_image_brand_profiles"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    visual_style: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Modern clean editorial, authentic, balanced depth and natural light",
    )
    preferred_composition: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Rule of thirds, clear focal subject, uncluttered background",
    )
    preferred_mood: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Professional, intelligent, inviting, authentic",
    )
    photography_preference: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    illustration_preference: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    logo_policy: Mapped[str] = mapped_column(String(64), nullable=False, default="NO_LOGOS")
    text_overlay_policy: Mapped[str] = mapped_column(String(64), nullable=False, default="NO_TEXT")
    aspect_ratio: Mapped[str] = mapped_column(String(32), nullable=False, default="16:9")
    quality: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    __table_args__ = (
        Index("ix_aibp_site", "site_id"),
    )
