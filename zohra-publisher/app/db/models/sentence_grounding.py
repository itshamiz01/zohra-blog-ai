"""
Zohra — SentenceGrounding model.

Stores fine-grained sentence-level evidence grounding records.
Maps each generated material factual statement to underlying claim IDs and assesses grounding status.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class SentenceGrounding(ZohraBase):
    __tablename__ = "sentence_grounding"

    draft_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[str] = mapped_column(String(64), nullable=False)

    sentence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sentence_text: Mapped[str] = mapped_column(Text, nullable=False)
    sentence_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    claim_ids_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)

    grounding_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="grounded",
    )  # grounded, partially_grounded, ungrounded, non_factual, attribution_required

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    __table_args__ = (
        Index("ix_sg_version_section", "draft_version_id", "section_id"),
        Index("ix_sg_status", "grounding_status"),
    )
