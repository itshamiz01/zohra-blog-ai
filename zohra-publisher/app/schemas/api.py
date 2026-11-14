"""
Zohra — API response and common schemas.

Every API response wraps data in a predictable envelope:
  { success, data, error, request_id }
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


# ── Envelope ─────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""

    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None
    request_id: str | None = None


# ── Health ───────────────────────────────────────────────────────


class ServiceHealth(BaseModel):
    status: str  # "healthy" | "unhealthy"
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: dict[str, ServiceHealth]


# ── System Status ────────────────────────────────────────────────


class SystemStatusResponse(BaseModel):
    version: str
    environment: str
    database: str
    redis: str
    worker: str
    queued_jobs: int = 0
    running_jobs: int = 0
    failed_jobs: int = 0
    daily_ai_cost: float = 0.0
    monthly_ai_cost: float = 0.0
    daily_budget: float = 0.0
    monthly_budget: float = 0.0
    autonomy_enabled: bool = False
    maintenance_mode: bool = False
    feature_flags: dict[str, bool] = {}
    providers: dict[str, Any] = {}


# ── Auth ─────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ── Jobs ─────────────────────────────────────────────────────────


class JobCreate(BaseModel):
    job_type: str
    priority: int = 0
    payload: dict[str, Any] | None = None
    scheduled_for: datetime | None = None
    max_attempts: int = 3
    idempotency_key: str | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    status: str
    priority: int
    payload: dict[str, Any] | None = None
    scheduled_for: datetime | None = None
    attempts: int = 0
    max_attempts: int = 3
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class JobTransition(BaseModel):
    new_status: str


# ── Agent Runs ───────────────────────────────────────────────────


class AgentRunCreate(BaseModel):
    agent_name: str
    agent_version: str = "0.1.0"
    task_type: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    input_summary: str | None = None
    metadata_json: dict[str, Any] | None = None


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_name: str
    agent_version: str
    task_type: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    provider: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


# ── Cost ─────────────────────────────────────────────────────────


class CostSummary(BaseModel):
    daily_total: float = 0.0
    monthly_total: float = 0.0
    daily_budget: float = 0.0
    monthly_budget: float = 0.0
    daily_remaining: float = 0.0
    monthly_remaining: float = 0.0
    currency: str = "USD"
    by_provider: dict[str, float] = {}
    by_model: dict[str, float] = {}


# ── Audit ────────────────────────────────────────────────────────


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_type: str
    actor_id: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    previous_state: str | None = None
    new_state: str | None = None
    created_at: datetime


# ── System Settings ──────────────────────────────────────────────


class SettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str | None = None
    value_type: str = "string"
    description: str | None = None
    # is_secret is intentionally EXCLUDED — secrets show value=None


class SettingUpdate(BaseModel):
    value: str
    description: str | None = None
