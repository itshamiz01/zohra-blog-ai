"""
Zohra — Operational Command Center & Autonomy API (Part 10).

Provides:
- Real-time operational snapshot
- Global Autonomy Kill Switch (/autonomy/pause, /autonomy/resume)
- Maintenance mode toggle
- Backlog freshness revalidation
- Dead-letter inspection and safe retries
- Full article lineage and operational pipeline overview
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_role
from app.db.models.jobs import Job
from app.db.models.operations import SecurityEvent, UserRole
from app.db.models.published_articles import PublishedArticle
from app.db.models.sites import Site
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.operations import (
    AutonomyPauseRequest,
    AutonomyResumeRequest,
    AutonomyStatusResponse,
    DeadLetterJobResponse,
    MaintenanceModeRequest,
    SystemSnapshotResponse,
)
from app.services.governor import CostGovernor
from app.services.recovery import RecoveryManager

router = APIRouter(prefix="/operations", tags=["Operations & Autonomy"])


@router.get("/snapshot", response_model=ApiResponse[SystemSnapshotResponse])
async def get_system_snapshot(
    _user: Annotated[Any, Depends(require_role(UserRole.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SystemSnapshotResponse]:
    """Retrieve full operational system snapshot."""
    recovery = RecoveryManager(db)
    snapshot = await recovery.get_system_snapshot()
    return ApiResponse(success=True, data=SystemSnapshotResponse(**snapshot))


@router.get("/autonomy", response_model=ApiResponse[AutonomyStatusResponse])
async def get_autonomy_status(
    _user: Annotated[Any, Depends(require_role(UserRole.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[AutonomyStatusResponse]:
    """Retrieve current autonomy status and cost degradation mode."""
    recovery = RecoveryManager(db)
    governor = CostGovernor(db)
    metrics = await governor.get_spend_metrics()

    site_res = await db.execute(select(Site).where(Site.enabled.is_(True)))
    sites_online = len(site_res.scalars().all())

    return ApiResponse(
        success=True,
        data=AutonomyStatusResponse(
            autonomy_status="PAUSED" if recovery.is_autonomy_paused() else "ACTIVE",
            autonomy_mode="PAUSED" if recovery.is_autonomy_paused() else "POLICY_CONTROLLED",
            maintenance_mode=recovery.is_maintenance_mode(),
            kill_switch_active=recovery.is_autonomy_paused(),
            sites_online=sites_online,
            spend_today_usd=metrics["spend_today_usd"],
            cost_mode=metrics["current_mode"],
        ),
    )


@router.post("/autonomy/pause", response_model=ApiResponse[dict[str, Any]])
async def pause_autonomy(
    payload: AutonomyPauseRequest,
    user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Emergency Kill Switch: Immediately halt all new autonomous publishing actions."""
    RecoveryManager.pause_autonomy()

    # Audit the kill switch invocation
    sec_event = SecurityEvent(
        event_type="EMERGENCY_KILL_SWITCH_ACTIVATED",
        severity="CRITICAL",
        actor_ref=user.username,
        details_json={"reason": payload.reason},
    )
    db.add(sec_event)
    await db.flush()

    return ApiResponse(
        success=True,
        data={
            "autonomy_status": "PAUSED",
            "message": "Global emergency kill switch engaged. Autonomous actions paused.",
            "audited_reason": payload.reason,
        },
    )


@router.post("/autonomy/resume", response_model=ApiResponse[dict[str, Any]])
async def resume_autonomy(
    payload: AutonomyResumeRequest,
    user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Resume autonomous publishing operations."""
    RecoveryManager.resume_autonomy()

    sec_event = SecurityEvent(
        event_type="AUTONOMY_RESUMED",
        severity="INFO",
        actor_ref=user.username,
        details_json={"reason": payload.reason},
    )
    db.add(sec_event)
    await db.flush()

    return ApiResponse(
        success=True,
        data={
            "autonomy_status": "ACTIVE",
            "message": "Autonomous publishing operations resumed under configured policies.",
            "audited_reason": payload.reason,
        },
    )


@router.post("/maintenance", response_model=ApiResponse[dict[str, Any]])
async def set_maintenance_mode(
    payload: MaintenanceModeRequest,
    user: Annotated[Any, Depends(require_role(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Toggle global platform maintenance mode."""
    RecoveryManager.set_maintenance_mode(payload.enabled)

    sec_event = SecurityEvent(
        event_type="MAINTENANCE_MODE_TOGGLED",
        severity="WARNING",
        actor_ref=user.username,
        details_json={"enabled": payload.enabled, "reason": payload.reason},
    )
    db.add(sec_event)
    await db.flush()

    return ApiResponse(
        success=True,
        data={
            "maintenance_mode": payload.enabled,
            "message": f"Maintenance mode set to {payload.enabled}.",
        },
    )


@router.post("/backlog/revalidate", response_model=ApiResponse[dict[str, Any]])
async def revalidate_backlog(
    user: Annotated[Any, Depends(require_role(UserRole.EDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: uuid.UUID | None = None,
) -> ApiResponse[dict[str, Any]]:
    """Revalidate queued backlog after downtime to catch stale breaking news."""
    recovery = RecoveryManager(db)
    result = await recovery.revalidate_queued_backlog(site_id=site_id)
    return ApiResponse(success=True, data=result)


@router.get("/dead-letter", response_model=ApiResponse[list[DeadLetterJobResponse]])
async def list_dead_letter_jobs(
    _user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[DeadLetterJobResponse]]:
    """Inspect dead-letter jobs that failed maximum retries."""
    query = (
        select(Job)
        .where(Job.status.in_(["FAILED", "DEAD_LETTER"]))
        .order_by(desc(Job.created_at))
        .limit(50)
    )
    res = await db.execute(query)
    jobs = res.scalars().all()

    items = [
        DeadLetterJobResponse(
            job_id=str(j.id),
            task_name=j.task_name,
            site_id=str(j.site_id) if getattr(j, "site_id", None) else None,
            failed_at=j.completed_at.isoformat() if j.completed_at else j.created_at.isoformat(),
            retry_count=j.attempts,
            error_message=j.error or "Unknown worker failure",
        )
        for j in jobs
    ]
    return ApiResponse(success=True, data=items)


@router.post("/dead-letter/{job_id}/retry", response_model=ApiResponse[dict[str, Any]])
async def retry_dead_letter_job(
    job_id: uuid.UUID,
    user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Safely reset and retry a dead-letter job."""
    query = select(Job).where(Job.id == job_id)
    res = await db.execute(query)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.status = "PENDING"
    job.error = None
    job.attempts = 0
    await db.flush()

    return ApiResponse(
        success=True,
        data={"job_id": str(job.id), "status": "PENDING", "message": "Job scheduled for retry."},
    )


@router.get("/pipeline", response_model=ApiResponse[list[dict[str, Any]]])
async def get_content_pipeline(
    _user: Annotated[Any, Depends(require_role(UserRole.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
) -> ApiResponse[list[dict[str, Any]]]:
    """Unified content pipeline view."""
    query = select(PublishedArticle)
    if site_id:
        query = query.where(PublishedArticle.site_id == site_id)
    query = query.order_by(desc(PublishedArticle.created_at)).limit(limit)

    res = await db.execute(query)
    articles = res.scalars().all()

    pipeline_items = [
        {
            "id": str(a.id),
            "article_id": str(a.article_id),
            "title": a.title,
            "site_id": str(a.site_id),
            "stage": a.status,
            "url": a.url,
            "verification_status": a.verification_status,
            "wordpress_post_id": a.wordpress_post_id,
            "created_at": a.created_at.isoformat(),
            "published_at": a.published_at.isoformat() if a.published_at else None,
        }
        for a in articles
    ]
    return ApiResponse(success=True, data=pipeline_items)


@router.get("/lineage/{article_id}", response_model=ApiResponse[dict[str, Any]])
async def get_article_lineage(
    article_id: uuid.UUID,
    _user: Annotated[Any, Depends(require_role(UserRole.VIEWER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Complete operational lineage of an article across all 10 stages."""
    query = select(PublishedArticle).where(
        (PublishedArticle.id == article_id) | (PublishedArticle.article_id == article_id)
    )
    res = await db.execute(query)
    article = res.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found in published registry")

    lineage = {
        "article_id": str(article.article_id),
        "published_record_id": str(article.id),
        "title": article.title,
        "slug": article.slug,
        "site_id": str(article.site_id),
        "draft_version_id": str(article.draft_version_id),
        "audit_id": str(article.audit_id),
        "publication_job_id": str(article.publication_job_id),
        "wordpress_post_id": article.wordpress_post_id,
        "url": article.url,
        "status": article.status,
        "verification_status": article.verification_status,
        "lifecycle_timeline": [
            {"stage": "DISCOVERED", "timestamp": article.created_at.isoformat()},
            {"stage": "VERIFIED", "status": article.verification_status, "timestamp": article.created_at.isoformat()},
            {"stage": "PUBLISHED", "wordpress_id": article.wordpress_post_id, "timestamp": article.published_at.isoformat() if article.published_at else None},
        ],
    }
    return ApiResponse(success=True, data=lineage)
