"""
Zohra — EvidenceItem model.

Connects claims to specific source document versions, tracking support direction
(supports, contradicts, partially_supports, context_only), evidence excerpts, and strength.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class EvidenceItem(ZohraBase):
    __tablename__ = "evidence_items"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # direct_quote, data_table, official_statement, secondary_reporting, community_observation
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="secondary_reporting", index=True
    )

    # supports, contradicts, partially_supports, context_only
    support_direction: Mapped[str] = mapped_column(
        String(50), nullable=False, default="supports", index=True
    )

    evidence_text_reference: Mapped[str] = mapped_column(Text, nullable=False)
    source_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_strength_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_evidence_claim_direction", "claim_id", "support_direction"),
        Index("ix_evidence_source_direction", "research_source_id", "support_direction"),
    )
