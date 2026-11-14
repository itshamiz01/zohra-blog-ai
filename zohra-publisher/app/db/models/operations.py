"""
Zohra — Production Operations & Command Center Database Models (Part 10).

Provides:
- User & Role-Based Access Control (RBAC) with per-site permission mappings
- Alerts, AlertManager state, deduplication, and notification delivery logs
- Transactional Outbox for cross-subsystem event publishing
- Scheduled task registry for Celery Beat coordination and visibility
- Security event logging and threat audit
- Encrypted secret records with versioning and rotation tracking
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase

# ── Enums ─────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class AutonomyMode(str, enum.Enum):
    OFF = "OFF"
    MANUAL = "MANUAL"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    DRAFT_ONLY = "DRAFT_ONLY"
    AUTO_LOW_RISK = "AUTO_LOW_RISK"
    POLICY_CONTROLLED = "POLICY_CONTROLLED"


class AlertCategory(str, enum.Enum):
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    PUBLISHING = "PUBLISHING"
    ANALYTICS = "ANALYTICS"
    COST = "COST"
    INTEGRATION = "INTEGRATION"
    CONTENT = "CONTENT"
    OPTIMIZATION = "OPTIMIZATION"
    DATABASE = "DATABASE"
    WORKER = "WORKER"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class NotificationChannel(str, enum.Enum):
    DASHBOARD = "DASHBOARD"
    EMAIL = "EMAIL"
    TELEGRAM = "TELEGRAM"
    WEBHOOK = "WEBHOOK"


class OutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    FAILED = "FAILED"


# ── 1. Users & RBAC ───────────────────────────────────────────────────

class User(ZohraBase):
    """System user with global role assignment."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.VIEWER.value, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site_roles = relationship("UserSiteRole", back_populates="user", cascade="all, delete-orphan")


class UserSiteRole(ZohraBase):
    """Scoped per-site role mapping for multi-tenant isolation."""

    __tablename__ = "user_site_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.VIEWER.value)

    user = relationship("User", back_populates="site_roles")

    __table_args__ = (
        UniqueConstraint("user_id", "site_id", name="uq_user_site_role"),
    )


# ── 2. Alerting & Notifications ───────────────────────────────────────

class Alert(ZohraBase):
    """Operational alert emitted by health monitors, jobs, or safety checks."""

    __tablename__ = "alerts"

    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, default=AlertCategory.SYSTEM.value, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default=AlertSeverity.INFO.value, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=AlertStatus.OPEN.value, index=True)
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class NotificationLog(ZohraBase):
    """Delivery record for external notifications (Telegram, Email, Webhooks)."""

    __tablename__ = "notification_logs"

    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    recipient_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SENT", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class NotificationPreference(ZohraBase):
    """Operator alert routing rules and quiet hours."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    channels_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=lambda: ["DASHBOARD"])
    severity_threshold: Mapped[str] = mapped_column(String(32), nullable=False, default=AlertSeverity.WARNING.value)
    categories_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "22:00"
    quiet_hours_end: Mapped[str | None] = mapped_column(String(10), nullable=True)    # "08:00"
    allow_critical_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# ── 3. Transactional Outbox ───────────────────────────────────────────

class OutboxEvent(ZohraBase):
    """Guaranteed cross-subsystem event publishing."""

    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=OutboxStatus.PENDING.value, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── 4. Scheduled Tasks Registry ───────────────────────────────────────

class ScheduledTaskRegistry(ZohraBase):
    """Operational registry for background Celery Beat jobs."""

    __tablename__ = "scheduled_tasks"

    task_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    cron_expression: Mapped[str] = mapped_column(String(64), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    site_scope_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=True,
    )


# ── 5. Security Events & Threat Audit ──────────────────────────────────

class SecurityEvent(ZohraBase):
    """Audit log for authentication attempts, permission violations, and injection threats."""

    __tablename__ = "security_events"

    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="WARNING", index=True)
    actor_ref: Mapped[str] = mapped_column(String(128), nullable=False, default="ANONYMOUS")
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)


# ── 6. Encrypted Secret Records ────────────────────────────────────────

class SecretRecord(ZohraBase):
    """Encrypted credential storage with versioning and rotation tracking."""

    __tablename__ = "secret_records"

    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    secret_key_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    key_derivation_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    last_rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    __table_args__ = (
        UniqueConstraint("site_id", "secret_key_name", "version", name="uq_secret_site_key_ver"),
    )
