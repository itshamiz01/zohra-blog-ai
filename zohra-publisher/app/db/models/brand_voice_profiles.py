"""
Zohra — BrandVoiceProfile model.

Defines site-level and editorial brand voice specifications:
tone, formality, vocabulary level, humor, directness, preferred patterns, and patterns to avoid.
Note: Brand voice alters rhythm and style, never factual meaning.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class BrandVoiceProfile(ZohraBase):
    __tablename__ = "brand_voice_profiles"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    tone: Mapped[str] = mapped_column(String(64), nullable=False, default="professional_approachable")
    formality: Mapped[str] = mapped_column(String(32), nullable=False, default="neutral")
    sentence_style: Mapped[str] = mapped_column(String(64), nullable=False, default="clear_concise")
    vocabulary_level: Mapped[str] = mapped_column(String(32), nullable=False, default="intermediate")

    preferred_patterns_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    avoid_patterns_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    humor_level: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    technical_depth: Mapped[str] = mapped_column(String(32), nullable=False, default="moderate")
    directness: Mapped[str] = mapped_column(String(32), nullable=False, default="high")

    examples_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_bvp_site_id", "site_id"),
    )
