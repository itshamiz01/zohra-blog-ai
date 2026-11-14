"""
Zohra — System status and job management endpoints.

GET  /api/v1/system/status      — full system status (admin)
POST /api/v1/system/jobs         — create a job
GET  /api/v1/system/jobs/{id}    — get job status
PUT  /api/v1/system/jobs/{id}    — transition job status
GET  /api/v1/system/costs        — cost summary
POST /api/v1/system/worker/test  — test Celery worker
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import JobStatus
from app.core.logging import get_logger
from app.core.security import require_admin_token

logger = get_logger(__name__, component="system_api")
from app.db.models.jobs import Job
from app.db.session import check_database_health, get_db
from app.schemas.api import (
    ApiResponse,
    CostSummary,
    JobCreate,
    JobResponse,
    JobTransition,
    SystemStatusResponse,
)
from app.llm.registry import get_provider_status
from app.services.cost import CostService
from app.utils.redis import check_redis_health

router = APIRouter(prefix="/system", tags=["System"])


# ── System Status ────────────────────────────────────────────────


@router.get("/status", response_model=ApiResponse[SystemStatusResponse])
async def system_status(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SystemStatusResponse]:
    """Full system status — admin only."""
    settings = get_settings()

    db_ok = await check_database_health()
    redis_ok = await check_redis_health()

    # Job counts
    queued = await db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.PENDING.value)
    )
    running = await db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.RUNNING.value)
    )
    failed = await db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.FAILED.value)
    )

    cost = await CostService.get_cost_summary(db)

    # Worker status via Celery inspect (best-effort)
    worker_status = "unknown"
    try:
        from app.workers.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=2.0)
        ping_result = inspect.ping()
        worker_status = "healthy" if ping_result else "unavailable"
    except Exception as exc:
        logger.debug("Worker inspect ping unavailable: %s", exc)
        worker_status = "unavailable"

    provider_status = get_provider_status()

    data = SystemStatusResponse(
        version=settings.APP_VERSION,
        environment=settings.APP_ENV.value,
        database="healthy" if db_ok else "unhealthy",
        redis="healthy" if redis_ok else "unhealthy",
        worker=worker_status,
        queued_jobs=queued.scalar_one(),
        running_jobs=running.scalar_one(),
        failed_jobs=failed.scalar_one(),
        daily_ai_cost=cost.daily_total,
        monthly_ai_cost=cost.monthly_total,
        daily_budget=cost.daily_budget,
        monthly_budget=cost.monthly_budget,
        autonomy_enabled=settings.AUTONOMY_ENABLED,
        maintenance_mode=settings.MAINTENANCE_MODE,
        feature_flags={
            "discovery": settings.ENABLE_DISCOVERY,
            "research": settings.ENABLE_RESEARCH,
            "writing": settings.ENABLE_WRITING,
            "auto_publish": settings.ENABLE_AUTO_PUBLISH,
            "analytics": settings.ENABLE_ANALYTICS,
        },
        providers=provider_status,
    )

    return ApiResponse(success=True, data=data)


@router.get("/providers", response_model=ApiResponse[dict[str, Any]])
async def providers_status(
    _token: Annotated[dict, Depends(require_admin_token)],
) -> ApiResponse[dict[str, Any]]:
    """Provider health and routing status — admin only, safe from secret exposure."""
    return ApiResponse(success=True, data=get_provider_status())


# ── Jobs ─────────────────────────────────────────────────────────


@router.post("/jobs", response_model=ApiResponse[JobResponse], status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[JobResponse]:
    """Create a background job."""
    # Idempotency check
    if payload.idempotency_key:
        existing = await db.execute(
            select(Job).where(Job.idempotency_key == payload.idempotency_key)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job with idempotency key '{payload.idempotency_key}' already exists",
            )

    job = Job(
        job_type=payload.job_type,
        priority=payload.priority,
        payload=payload.payload,
        scheduled_for=payload.scheduled_for,
        max_attempts=payload.max_attempts,
        idempotency_key=payload.idempotency_key,
        status=JobStatus.PENDING.value if not payload.scheduled_for else JobStatus.SCHEDULED.value,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    return ApiResponse(success=True, data=JobResponse.model_validate(job))


@router.get("/jobs/{job_id}", response_model=ApiResponse[JobResponse])
async def get_job(
    job_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[JobResponse]:
    """Get a job by ID."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ApiResponse(success=True, data=JobResponse.model_validate(job))


@router.put("/jobs/{job_id}/status", response_model=ApiResponse[JobResponse])
async def transition_job(
    job_id: uuid.UUID,
    body: JobTransition,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[JobResponse]:
    """Transition a job to a new status."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Validate the new status is a known JobStatus
    try:
        new_status = JobStatus(body.new_status)
    except ValueError as err:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {body.new_status}. Valid: {[s.value for s in JobStatus]}",
        ) from err

    job.status = new_status.value

    # Update timestamps based on transition
    now = datetime.now(UTC)
    if new_status == JobStatus.RUNNING:
        job.started_at = now
        job.attempts += 1
    elif new_status in (
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.DEAD_LETTER,
    ):
        job.completed_at = now

    await db.flush()
    await db.refresh(job)

    return ApiResponse(success=True, data=JobResponse.model_validate(job))


# ── Cost ─────────────────────────────────────────────────────────


@router.get("/costs", response_model=ApiResponse[CostSummary])
async def get_costs(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[CostSummary]:
    """Get AI cost summary."""
    summary = await CostService.get_cost_summary(db)
    return ApiResponse(success=True, data=summary)


# ── Worker Test ──────────────────────────────────────────────────


@router.post("/worker/test", response_model=ApiResponse)
async def test_worker(
    _token: Annotated[dict, Depends(require_admin_token)],
) -> ApiResponse:
    """
    Dispatch a test task to the Celery worker.
    Proves: FastAPI → Redis → Worker → Result backend.
    """
    from app.workers.tasks import system_health_check

    result = system_health_check.delay()

    return ApiResponse(
        success=True,
        data={
            "task_id": result.id,
            "status": "dispatched",
            "message": "Health check task sent to worker. Check task status via Celery result backend.",
        },
    )


# ── Autonomy Kill Switch & Resume (Prompt #15) ─────────────────────

@router.post("/autonomy/pause", response_model=ApiResponse[dict])
async def system_pause_autonomy(
    _token: Annotated[dict, Depends(require_admin_token)],
) -> ApiResponse[dict]:
    """Emergency kill switch: Pause all autonomous actions."""
    from app.services.recovery import RecoveryManager
    RecoveryManager.pause_autonomy()
    return ApiResponse(
        success=True,
        data={"autonomy_status": "PAUSED", "message": "Emergency kill switch engaged."}
    )


@router.post("/autonomy/resume", response_model=ApiResponse[dict])
async def system_resume_autonomy(
    _token: Annotated[dict, Depends(require_admin_token)],
) -> ApiResponse[dict]:
    """Resume autonomous actions."""
    from app.services.recovery import RecoveryManager
    RecoveryManager.resume_autonomy()
    return ApiResponse(
        success=True,
        data={"autonomy_status": "ACTIVE", "message": "Autonomous operations resumed."}
    )
