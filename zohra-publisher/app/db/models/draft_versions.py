"""
Zohra — DraftVersion model.

Stores immutable snapshots of generated article text, structured content sections,
grounding scores, quality scores, and revision justifications.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class DraftVersion(ZohraBase):
    __tablename__ = "draft_versions"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    slug_candidate: Mapped[str] = mapped_column(String(256), nullable=False)

    meta_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    sections_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    faq_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    tables_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    generation_reason: Mapped[str] = mapped_column(String(64), nullable=False, default="initial_generation")

    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    grounding_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_dv_project_version", "draft_project_id", "version_number"),
    )
