"""
Zohra — Operations & Command Center Pydantic V2 Schemas (Part 10).

Provides:
- User management and RBAC request/response models
- Autonomy control and kill switch schemas
- Operational alerts and notification preference schemas
- Database backup creation, listing, and verification models
- System health, snapshot, and dead-letter queue models
- Secret metadata models with zero secret content leakage
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.db.models.operations import (
    AlertCategory,
    AlertSeverity,
    UserRole,
)

# ── 1. Users & RBAC ───────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER
    is_active: bool = True


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserSiteRoleAssignment(BaseModel):
    site_id: uuid.UUID
    role: UserRole


# ── 2. Autonomy Controls & Kill Switch ─────────────────────────────────

class AutonomyStatusResponse(BaseModel):
    autonomy_status: str  # "ACTIVE" | "PAUSED"
    autonomy_mode: str
    maintenance_mode: bool
    kill_switch_active: bool
    sites_online: int
    spend_today_usd: float
    cost_mode: str


class AutonomyPauseRequest(BaseModel):
    reason: str = Field(..., min_length=5, description="Audited operational reason for pausing autonomy")


class AutonomyResumeRequest(BaseModel):
    reason: str = Field(..., min_length=5, description="Audited operational reason for resuming autonomy")


class MaintenanceModeRequest(BaseModel):
    enabled: bool
    reason: str = Field(..., min_length=5)


# ── 3. Alerts & Notifications ──────────────────────────────────────────

class AlertCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=5)
    category: AlertCategory = AlertCategory.SYSTEM
    severity: AlertSeverity = AlertSeverity.WARNING
    source: str = "operator"
    site_id: uuid.UUID | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID | None = None
    category: str
    severity: str
    title: str
    message: str
    source: str
    entity_type: str | None = None
    entity_id: str | None = None
    status: str
    occurrence_count: int
    metadata_json: dict[str, Any]
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── 4. Backups ─────────────────────────────────────────────────────────

class BackupItemResponse(BaseModel):
    backup_name: str
    created_at: str
    size_bytes: int
    checksum_sha256: str
    is_encrypted: bool
    verification_status: str


class BackupVerifyResponse(BaseModel):
    status: str
    verified_at: str
    manifest: dict[str, Any]


class BackupRestoreTestResponse(BaseModel):
    backup_name: str
    sandbox_restore_success: bool
    tested_at: str


# ── 5. Secrets (Zero Leaks) ───────────────────────────────────────────

class SecretCreateRequest(BaseModel):
    key_name: str = Field(..., min_length=2, max_length=128)
    value: str = Field(..., min_length=1)
    site_id: uuid.UUID | None = None


class SecretMetadataResponse(BaseModel):
    id: str | None = None
    key_name: str
    version: int
    status: str
    last_rotated_at: str | None = None
    is_active: bool


# ── 6. Operational Snapshots & Dead Letter ─────────────────────────────

class SystemSnapshotResponse(BaseModel):
    autonomy_status: str
    maintenance_mode: bool
    sites_total: int
    sites_online: int
    published_today: int
    articles_in_pipeline: int
    pending_approvals: int
    spend_today_usd: float
    daily_budget_usd: float
    cost_mode: str
    version: str
    snapshot_timestamp: str


class DeadLetterJobResponse(BaseModel):
    job_id: str
    task_name: str
    site_id: str | None = None
    failed_at: str
    retry_count: int
    error_message: str


class JobRetryRequest(BaseModel):
    job_id: str
