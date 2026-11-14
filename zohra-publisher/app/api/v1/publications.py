"""
Zohra — Publishing REST API Endpoints (Part 7).

Endpoints:
- POST /api/v1/publications: Enqueue / initiate publication job
- GET  /api/v1/publications: List publication jobs
- GET  /api/v1/publications/{id}: Get job details
- GET  /api/v1/publications/{id}/preview: Retrieve rendered preview without publishing
- POST /api/v1/publications/{id}/approve: Admin approval for previewed draft
- POST /api/v1/publications/{id}/publish: Trigger immediate publication
- POST /api/v1/publications/{id}/schedule: Schedule approved publication
- POST /api/v1/publications/{id}/reconcile: Reconcile network/status discrepancies
- GET  /api/v1/sites/{id}/health: WordPress connection health probe
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.rbac import require_role
from app.core.security import require_admin_token
from app.db.models.final_audit_packages import FinalAuditPackage
from app.db.models.operations import UserRole
from app.db.models.publication_jobs import PublicationJob
from app.db.models.published_articles import PublicationApproval
from app.db.models.sites import Site
from app.db.session import get_db

logger = get_logger(__name__, component="publishing_api")

from app.schemas.api import ApiResponse
from app.schemas.publishing import (
    ApprovalAction,
    PublicationApprovalRequest,
    PublicationCreateRequest,
    PublicationJobResponse,
)

router = APIRouter(prefix="/publications", tags=["Publishing Engine"])


@router.post("", response_model=ApiResponse[PublicationJobResponse], status_code=status.HTTP_201_CREATED)
async def create_publication_job(
    payload: PublicationCreateRequest,
    _user: Annotated[Any, Depends(require_role(UserRole.EDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PublicationJobResponse]:
    """Enqueue a publication job for a Part 6-approved article."""
    site = await db.get(Site, payload.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Fetch audit package
    stmt = select(FinalAuditPackage).where(FinalAuditPackage.audit_project_id == payload.audit_id)
    res = await db.execute(stmt)
    fap = res.scalar_one_or_none()
    if not fap:
        raise HTTPException(status_code=404, detail="Final audit package not found")

    if fap.decision != "PASS" or not fap.eligible_for_part7:
        raise HTTPException(status_code=400, detail="Draft has not passed independent audit or is ineligible")

    idempotency_key = f"pub:{payload.site_id}:{payload.draft_version_id}:{payload.audit_id}"

    existing = await db.execute(select(PublicationJob).where(PublicationJob.idempotency_key == idempotency_key))
    existing_job = existing.scalar_one_or_none()
    if existing_job:
        return ApiResponse(data=PublicationJobResponse.model_validate(existing_job))

    job = PublicationJob(
        site_id=payload.site_id,
        article_id=payload.draft_version_id,
        draft_version_id=payload.draft_version_id,
        audit_id=payload.audit_id,
        idempotency_key=idempotency_key,
        content_hash=fap.content_hash,
        publication_mode=payload.publication_mode.value,
        desired_status=payload.desired_status,
        scheduled_for=payload.scheduled_for,
        status="CREATED",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Trigger background Celery task
    try:
        from app.workers.celery_app import celery_app
        celery_app.send_task("publication.start_job", args=[str(job.id)])
    except Exception as exc:
        logger.warning("Failed to dispatch Celery task 'publication.start_job' for job %s: %s", job.id, exc)

    return ApiResponse(data=PublicationJobResponse.model_validate(job))


@router.get("", response_model=ApiResponse[list[PublicationJobResponse]])
async def list_publication_jobs(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ApiResponse[list[PublicationJobResponse]]:
    """List publication jobs with status/site filtering."""
    stmt = select(PublicationJob)
    if site_id:
        stmt = stmt.where(PublicationJob.site_id == site_id)
    if status_filter:
        stmt = stmt.where(PublicationJob.status == status_filter)
    stmt = stmt.order_by(PublicationJob.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    jobs = list(res.scalars().all())
    return ApiResponse(data=[PublicationJobResponse.model_validate(j) for j in jobs])


@router.get("/{job_id}", response_model=ApiResponse[PublicationJobResponse])
async def get_publication_job(
    job_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PublicationJobResponse]:
    """Retrieve publication job by ID."""
    job = await db.get(PublicationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Publication job not found")
    return ApiResponse(data=PublicationJobResponse.model_validate(job))


@router.get("/{job_id}/preview", response_model=ApiResponse[dict])
async def get_publication_preview(
    job_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Retrieve pre-rendered publication preview."""
    job = await db.get(PublicationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Publication job not found")
    return ApiResponse(data=job.preview_json or {"html": job.rendered_html or ""})


@router.post("/{job_id}/approve", response_model=ApiResponse[dict])
async def approve_publication(
    job_id: UUID,
    payload: PublicationApprovalRequest,
    current_user: Annotated[Any, Depends(require_role(UserRole.EDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Admin/Editor approval gate before live publication."""
    job = await db.get(PublicationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Publication job not found")

    actor = getattr(current_user, "username", None) or getattr(current_user, "user_id", "admin")
    approval = PublicationApproval(
        publication_job_id=job.id,
        actor_id=str(actor),
        action=payload.action.value,
        reason=payload.reason,
        payload_hash=job.payload_hash or job.content_hash,
    )
    db.add(approval)

    if payload.action == ApprovalAction.APPROVE:
        job.status = "APPROVED_FOR_PUBLICATION"
    elif payload.action == ApprovalAction.REJECT:
        job.status = "CANCELLED"

    await db.commit()
    return ApiResponse(data={"job_id": str(job.id), "status": job.status, "action": payload.action.value})
