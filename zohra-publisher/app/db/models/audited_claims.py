"""
Zohra — AuditedClaim model (Part 6).

Factual claims independently re-extracted from generated draft prose
and matched against Part 4 research knowledge records.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class AuditedClaim(ZohraBase):
    __tablename__ = "audited_claims"

    audit_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sentence_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_claim: Mapped[str] = mapped_column(Text, nullable=False)

    claim_type: Mapped[str] = mapped_column(String(64), nullable=False, default="factual")
    importance: Mapped[str] = mapped_column(String(32), nullable=False, default="supporting")  # critical, major, supporting

    matched_research_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    match_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTED, OUTDATED, MISLEADING, ATTRIBUTION_MISSING, SCOPE_MISMATCH
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False, default="UNSUPPORTED", index=True)

    entailment_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    audit_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_numbers: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    extracted_dates: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_ac_proj_status", "audit_project_id", "verification_status"),
    )
