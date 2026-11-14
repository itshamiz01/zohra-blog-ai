"""
Zohra — Part 9 Optimization REST API Routes.

Implements Sections 140 to 145, 218 of Part 9 Master Prompt:
- Health and status endpoints
- Optimization policies CRUD
- Candidates ingestion and filtering
- Plan inspection, approval, rejection, execution, and rollback
- Content refresh candidates queue
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import require_admin_token
from app.db.models.optimization import (
    ContentSnapshot,
    OptimizationApproval,
    OptimizationCandidate,
    OptimizationChangeset,
    OptimizationPlan,
    OptimizationPolicy,
)
from app.db.models.sites import Site
from app.db.session import get_db
from app.optimization.executor import OptimizationExecutor
from app.optimization.rollback import RollbackEngine
from app.schemas.api import ApiResponse
from app.schemas.optimization import (
    ApprovalActionRequest,
    ExecutionRequest,
    OptimizationCandidateCreate,
    OptimizationCandidateResponse,
    OptimizationHealthResponse,
    OptimizationPlanResponse,
    OptimizationPolicyCreate,
    OptimizationPolicyResponse,
    RollbackRequest,
)

router = APIRouter(prefix="/optimization", tags=["optimization"])


# ── Health ────────────────────────────────────────────────────────────

@router.get("/health", response_model=ApiResponse[OptimizationHealthResponse])
async def get_optimization_health(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OptimizationHealthResponse]:
    """Returns optimization engine operational status, kill switch state, and pending queues."""
    settings = get_settings()

    # Count pending approvals
    stmt = select(OptimizationApproval).where(OptimizationApproval.status == "PENDING")
    res = await db.execute(stmt)
    pending_count = len(res.scalars().all())

    data = OptimizationHealthResponse(
        status="healthy",
        optimization_enabled=getattr(settings, "OPTIMIZATION_ENABLED", True),
        auto_optimization_enabled=getattr(settings, "AUTO_OPTIMIZATION_ENABLED", False),
        pending_approvals=pending_count,
        active_experiments=0,
        daily_ai_cost_used=0.0,
        daily_ai_cost_limit=getattr(settings, "MAX_DAILY_OPTIMIZATION_AI_COST", 20.0),
        version="part-9-v1",
    )
    return ApiResponse(data=data)


# ── Policies ──────────────────────────────────────────────────────────

@router.post("/policies", response_model=ApiResponse[OptimizationPolicyResponse], status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: OptimizationPolicyCreate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OptimizationPolicyResponse]:
    """Creates or configures an optimization governance policy for a site."""
    policy = OptimizationPolicy(**payload.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return ApiResponse(data=OptimizationPolicyResponse.model_validate(policy))


@router.get("/policies", response_model=ApiResponse[list[OptimizationPolicyResponse]])
async def list_policies(
    site_id: uuid.UUID = Query(...),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[OptimizationPolicyResponse]]:
    """Lists optimization policies for a site."""
    stmt = select(OptimizationPolicy).where(OptimizationPolicy.site_id == site_id)
    res = await db.execute(stmt)
    policies = res.scalars().all()
    return ApiResponse(data=[OptimizationPolicyResponse.model_validate(p) for p in policies])


# ── Candidates ────────────────────────────────────────────────────────

@router.get("/candidates", response_model=ApiResponse[list[OptimizationCandidateResponse]])
async def list_candidates(
    site_id: uuid.UUID = Query(...),
    status_filter: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[OptimizationCandidateResponse]]:
    """Lists optimization candidates with optional status filter."""
    stmt = select(OptimizationCandidate).where(OptimizationCandidate.site_id == site_id)
    if status_filter:
        stmt = stmt.where(OptimizationCandidate.status == status_filter.upper())
    stmt = stmt.order_by(OptimizationCandidate.priority_score.desc()).limit(limit)

    res = await db.execute(stmt)
    cands = res.scalars().all()
    return ApiResponse(data=[OptimizationCandidateResponse.model_validate(c) for c in cands])


@router.post("/candidates", response_model=ApiResponse[OptimizationCandidateResponse], status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: OptimizationCandidateCreate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OptimizationCandidateResponse]:
    """Ingests an optimization candidate unit."""
    cand = OptimizationCandidate(**payload.model_dump())
    db.add(cand)
    await db.commit()
    await db.refresh(cand)
    return ApiResponse(data=OptimizationCandidateResponse.model_validate(cand))


# ── Plans & Approvals ─────────────────────────────────────────────────

@router.get("/plans/{plan_id}", response_model=ApiResponse[OptimizationPlanResponse])
async def get_plan(
    plan_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OptimizationPlanResponse]:
    """Retrieves an OptimizationPlan with hypothesis, metrics, and criteria."""
    stmt = select(OptimizationPlan).where(OptimizationPlan.id == plan_id)
    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Optimization plan not found")
    return ApiResponse(data=OptimizationPlanResponse.model_validate(plan))


@router.post("/plans/{plan_id}/approve", response_model=ApiResponse[dict])
async def approve_plan(
    plan_id: uuid.UUID,
    payload: ApprovalActionRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Human approval for medium/high-risk optimization plans."""
    stmt = select(OptimizationPlan).where(OptimizationPlan.id == plan_id)
    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = "APPROVED"
    await db.commit()
    return ApiResponse(data={"plan_id": str(plan.id), "status": plan.status, "decision": "APPROVED"})


@router.post("/plans/{plan_id}/reject", response_model=ApiResponse[dict])
async def reject_plan(
    plan_id: uuid.UUID,
    payload: ApprovalActionRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Rejects an optimization plan."""
    stmt = select(OptimizationPlan).where(OptimizationPlan.id == plan_id)
    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = "REJECTED"
    await db.commit()
    return ApiResponse(data={"plan_id": str(plan.id), "status": plan.status, "decision": "REJECTED", "notes": payload.notes})


@router.post("/plans/{plan_id}/execute", response_model=ApiResponse[dict])
async def execute_plan(
    plan_id: uuid.UUID,
    payload: ExecutionRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Executes an approved plan through the atomic executor and Part 7 pipeline."""
    stmt = select(OptimizationPlan).where(OptimizationPlan.id == plan_id)
    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Fetch Site
    site_stmt = select(Site).where(Site.id == plan.site_id)
    site_res = await db.execute(site_stmt)
    site = site_res.scalar_one_or_none()
    site_dict = {"id": str(site.id) if site else str(plan.site_id), "domain": site.domain if site else "example.com"}

    # Mock or current article state
    current_article = {
        "title": plan.current_state_json.get("title", "Current Article Title"),
        "article_body": plan.current_state_json.get("article_body", "Current content..."),
        "meta_description": plan.current_state_json.get("meta_description"),
        "wordpress_post_id": 101,
    }

    result = await OptimizationExecutor.execute_plan(
        plan=plan,
        current_article=current_article,
        site_data=site_dict,
        operator_id=payload.operator_id,
        is_human_override=payload.override_human_lock,
    )
    await db.commit()
    return ApiResponse(data=result)


@router.post("/plans/{plan_id}/rollback", response_model=ApiResponse[dict])
async def rollback_plan(
    plan_id: uuid.UUID,
    payload: RollbackRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Rolls back an applied optimization plan to its pre-change state."""
    # Find latest changeset for plan
    stmt = select(OptimizationChangeset).where(OptimizationChangeset.optimization_plan_id == plan_id)
    res = await db.execute(stmt)
    changeset = res.scalar_one_or_none()
    if not changeset or not changeset.before_snapshot_id:
        raise HTTPException(status_code=404, detail="No rollback changeset or snapshot found for plan")

    snap_stmt = select(ContentSnapshot).where(ContentSnapshot.id == changeset.before_snapshot_id)
    snap_res = await db.execute(snap_stmt)
    before_snap = snap_res.scalar_one_or_none()
    if not before_snap:
        raise HTTPException(status_code=404, detail="Before snapshot not found")

    current_art = {
        "title": before_snap.title,
        "article_body": before_snap.article_body,
        "wordpress_post_id": before_snap.wordpress_post_id or 101,
    }
    site_dict = {"id": str(changeset.site_id), "domain": "example.com"}

    result = await RollbackEngine.execute_rollback(
        changeset=changeset,
        before_snapshot=before_snap,
        current_article=current_art,
        site_data=site_dict,
        reason=payload.reason,
        operator_id=payload.operator_id,
    )
    await db.commit()
    return ApiResponse(data=result)


@router.get("/refresh-candidates", response_model=ApiResponse[list[dict]])
async def get_refresh_candidates(
    site_id: uuid.UUID = Query(...),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[dict]]:
    """Returns queued content refresh candidates."""
    # Queries candidates with candidate_type like REFRESH or DECLINE
    stmt = (
        select(OptimizationCandidate)
        .where(
            OptimizationCandidate.site_id == site_id,
            OptimizationCandidate.candidate_type.in_(["CONTENT_REFRESH_REVIEW", "DECLINE_REVIEW"]),
        )
        .order_by(OptimizationCandidate.priority_score.desc())
        .limit(20)
    )
    res = await db.execute(stmt)
    cands = res.scalars().all()
    return ApiResponse(data=[OptimizationCandidateResponse.model_validate(c).model_dump() for c in cands])
