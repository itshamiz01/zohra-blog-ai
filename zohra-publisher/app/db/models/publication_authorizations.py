"""
Zohra — Publication Authorization model (Part 7).

Internal publication authorization record generated when Part 6 delivers
a PASS decision. Tracks draft version, content hash, audit fingerprint,
expiration, and replay prevention status.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class PublicationAuthorization(ZohraBase):
    __tablename__ = "publication_authorizations"

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_version_id: Mapped[uuid.UUID] = mapped_column(
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

    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    audit_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    authorized_action: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLISH")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE", index=True)
    # Statuses: ACTIVE, USED, EXPIRED, REVOKED, INVALID

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_pub_auth_audit_status", "audit_id", "status"),
        Index("ix_pub_auth_hash", "content_hash"),
    )
