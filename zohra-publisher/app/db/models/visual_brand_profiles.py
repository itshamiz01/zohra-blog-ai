"""
Zohra — VisualBrandProfile model (Part 7).

Defines brand visual identity, typography, composition guidelines,
aspect ratios, and forbidden patterns for AI-generated and curated imagery.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class VisualBrandProfile(ZohraBase):
    __tablename__ = "visual_brand_profiles"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    visual_style: Mapped[str] = mapped_column(String(128), nullable=False, default="modern_editorial")
    composition_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    typography_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_policy: Mapped[str | None] = mapped_column(Text, nullable=True)

    preferred_aspect_ratios: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=lambda: ["16:9", "1200:630"])
    forbidden_visual_patterns: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)

    image_text_policy: Mapped[str] = mapped_column(String(64), nullable=False, default="disallow_baked_text")
    photorealism_policy: Mapped[str] = mapped_column(String(64), nullable=False, default="authentic_editorial")
    illustration_policy: Mapped[str] = mapped_column(String(64), nullable=False, default="minimalist_vector")

    palette_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    __table_args__ = (
        Index("ix_vbp_site_id", "site_id"),
    )
