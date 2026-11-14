"""
Zohra — ContentOverlapFinding model (Part 6).

Records findings from the originality and copyright-aware overlap engine,
including exact n-gram matches, competitor phrase overlaps, and structural mimicry.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ContentOverlapFinding(ZohraBase):
    __tablename__ = "content_overlap_findings"

    audit_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    draft_location: Mapped[str] = mapped_column(String(128), nullable=False)
    source_location: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # exact_ngram, fuzzy_overlap, semantic_paraphrase, structural_mimicry, site_cannibalization
    overlap_type: Mapped[str] = mapped_column(String(64), nullable=False, default="exact_ngram", index=True)

    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    matched_text_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    matched_text_sample: Mapped[str | None] = mapped_column(Text, nullable=True)

    # CRITICAL, MAJOR, MODERATE, MINOR, INFO
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MAJOR")

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_cof_proj_type", "audit_project_id", "overlap_type"),
    )
