"""
Zohra — MediaPlan & MediaAsset models (Part 7).

Manages planned visual requirements (featured image, charts, diagrams, screenshots)
and physical media assets with strict provenance, licensing rights, optimization,
and WordPress media attachment IDs.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class MediaPlan(ZohraBase):
    __tablename__ = "media_plans"

    publication_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # asset_type: FEATURED_IMAGE, ORIGINAL_CHART, ORIGINAL_DIAGRAM, SCREENSHOT, ILLUSTRATION, INFOGRAPHIC

    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    placement: Mapped[str] = mapped_column(String(64), nullable=False, default="featured")
    # placement: featured, section_intro, comparison_block, conclusion

    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_strategy: Mapped[str] = mapped_column(String(64), nullable=False, default="AI_GENERATED")
    # source_strategy: AI_GENERATED, ORIGINAL_CHART, ORIGINAL_DIAGRAM, SCREENSHOT, OFFICIAL_SOURCE, LICENSED_LIBRARY, NO_MEDIA

    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_aspect_ratio: Mapped[str] = mapped_column(String(32), nullable=False, default="16:9")
    target_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    target_height: Mapped[int] = mapped_column(Integer, nullable=False, default=675)

    alt_text_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rights_requirement: Mapped[str] = mapped_column(String(64), nullable=False, default="COMMERCIAL_ALLOWED")

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNED", index=True)
    # status: PLANNED, GENERATING, READY, FAILED, SKIPPED

    # Relationship to asset
    asset = relationship("MediaAsset", back_populates="media_plan", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_media_plan_job_asset", "publication_job_id", "asset_type"),
    )


class MediaAsset(ZohraBase):
    __tablename__ = "media_assets"

    media_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_plans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    origin_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # origin_type: AI_GENERATED, ORIGINAL_CHART, ORIGINAL_DIAGRAM, SCREENSHOT, OFFICIAL_SOURCE, LICENSED_LIBRARY

    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creator: Mapped[str | None] = mapped_column(String(255), nullable=True)

    license_type: Mapped[str] = mapped_column(String(64), nullable=False, default="PROPRIETARY_AI")
    license_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    attribution_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attribution_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    commercial_use_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    modification_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rights_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    rights_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    local_storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/webp")
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=675)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    alt_text: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    provenance_metadata: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    wordpress_media_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    wordpress_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    media_plan = relationship("MediaPlan", back_populates="asset")

    __table_args__ = (
        Index("ix_media_asset_hash", "content_hash"),
        Index("ix_media_asset_wp_id", "wordpress_media_id"),
    )
