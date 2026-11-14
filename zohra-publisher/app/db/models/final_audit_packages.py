"""
Zohra — FinalAuditPackage model (Part 6).

The immutable, cryptographically-hashed audit package handed off to Part 7.
Includes the signed audit token and eligibility flag. Part 7 verifies that
the current content hash matches the approved audit package before preparation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class FinalAuditPackage(ZohraBase):
    __tablename__ = "final_audit_packages"

    audit_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    research_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_package_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    eligible_for_part7: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    overall_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    factual_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grounding_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Cryptographic integrity tokens
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    audit_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    audit_token: Mapped[str] = mapped_column(String(256), nullable=False, index=True)

    package_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_fap_token", "audit_token", unique=True),
        Index("ix_fap_hash", "content_hash"),
    )
