"""
Zohra Part 3 — Content Opportunities API endpoints.

GET   /api/v1/opportunities
GET   /api/v1/opportunities/top
GET   /api/v1/opportunities/watchlist
GET   /api/v1/opportunities/{id}
GET   /api/v1/opportunities/{id}/keywords
GET   /api/v1/opportunities/{id}/serp
GET   /api/v1/opportunities/{id}/competitors
GET   /api/v1/opportunities/{id}/gaps
GET   /api/v1/opportunities/{id}/score
GET   /api/v1/opportunities/{id}/explanation
GET   /api/v1/opportunities/{id}/package
POST  /api/v1/opportunities/{id}/action
POST  /api/v1/opportunities/{id}/status
POST  /api/v1/opportunities/{id}/reanalyze
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import ContentAction, OpportunityStatus
from app.core.security import require_admin_token
from app.db.models.content_gaps import ContentGap
from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.opportunity_snapshots import OpportunityWatchlist
from app.db.models.serp import SERPResult, SERPSnapshot
from app.db.session import get_db
from app.opportunity.handoff import build_opportunity_package
from app.schemas.api import ApiResponse
from app.schemas.opportunity import (
    ContentActionOverrideRequest,
    ContentGapResponse,
    ContentOpportunityPackage,
    ContentOpportunityResponse,
    OpportunityExplanationResponse,
    OpportunityWatchlistResponse,
    SERPResultResponse,
)
from app.services.audit import AuditService

router = APIRouter(prefix="/opportunities", tags=["Content Opportunities"])


@router.get("", response_model=ApiResponse[list[ContentOpportunityResponse]])
async def list_opportunities(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    intent: str | None = None,
    content_type: str | None = None,
    recommended_action: str | None = None,
    language: str | None = None,
    min_score: float | None = Query(default=None, ge=0.0, le=100.0),
    min_confidence: float | None = Query(default=None, ge=0.0, le=100.0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[list[ContentOpportunityResponse]]:
    """List scored content opportunities with multi-dimensional filtering."""
    query = select(ContentOpportunity).order_by(desc(ContentOpportunity.opportunity_score))

    if site_id:
        query = query.where(ContentOpportunity.site_id == site_id)
    if status_filter:
        query = query.where(ContentOpportunity.status == status_filter)
    if intent:
        query = query.where(ContentOpportunity.primary_intent == intent)
    if content_type:
        query = query.where(ContentOpportunity.content_type == content_type)
    if recommended_action:
        query = query.where(ContentOpportunity.recommended_action == recommended_action)
    if language:
        query = query.where(ContentOpportunity.language == language)
    if min_score is not None:
        query = query.where(ContentOpportunity.opportunity_score >= min_score)
    if min_confidence is not None:
        query = query.where(ContentOpportunity.confidence_score >= min_confidence)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    opportunities = list(result.scalars().all())

    return ApiResponse(data=[ContentOpportunityResponse.model_validate(o) for o in opportunities])


@router.get("/top", response_model=ApiResponse[list[ContentOpportunityResponse]])
async def get_top_opportunities(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: UUID | None = None,
    limit: int = Query(default=10, ge=1, le=50),
) -> ApiResponse[list[ContentOpportunityResponse]]:
    """Returns top qualified opportunities eligible for publishing / research."""
    query = (
        select(ContentOpportunity)
        .where(
            ContentOpportunity.status.in_([
                OpportunityStatus.QUALIFIED.value,
                OpportunityStatus.HIGH_PRIORITY.value,
            ]),
            ContentOpportunity.opportunity_score >= 65.0,
        )
        .order_by(desc(ContentOpportunity.opportunity_score))
        .limit(limit)
    )
    if site_id:
        query = query.where(ContentOpportunity.site_id == site_id)

    result = await db.execute(query)
    opportunities = list(result.scalars().all())
    return ApiResponse(data=[ContentOpportunityResponse.model_validate(o) for o in opportunities])


@router.get("/watchlist", response_model=ApiResponse[list[OpportunityWatchlistResponse]])
async def get_opportunity_watchlist(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[OpportunityWatchlistResponse]]:
    """Returns active watchlist items awaiting developing signals or confirmation."""
    stmt = (
        select(OpportunityWatchlist)
        .where(OpportunityWatchlist.is_active.is_(True))
        .order_by(OpportunityWatchlist.recheck_after.asc())
    )
    res = await db.execute(stmt)
    entries = list(res.scalars().all())
    return ApiResponse(data=[OpportunityWatchlistResponse.model_validate(e) for e in entries])


@router.get("/{opportunity_id}", response_model=ApiResponse[ContentOpportunityResponse])
async def get_opportunity_detail(
    opportunity_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[ContentOpportunityResponse]:
    """Retrieve detailed opportunity record by ID."""
    opp = await db.get(ContentOpportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return ApiResponse(data=ContentOpportunityResponse.model_validate(opp))


@router.get("/{opportunity_id}/gaps", response_model=ApiResponse[list[ContentGapResponse]])
async def get_opportunity_gaps(
    opportunity_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[ContentGapResponse]]:
    """Retrieve identified structural content gaps for an opportunity."""
    stmt = select(ContentGap).where(ContentGap.opportunity_id == opportunity_id)
    res = await db.execute(stmt)
    gaps = list(res.scalars().all())
    return ApiResponse(data=[ContentGapResponse.model_validate(g) for g in gaps])


@router.get("/{opportunity_id}/serp", response_model=ApiResponse[list[SERPResultResponse]])
async def get_opportunity_serp(
    opportunity_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[SERPResultResponse]]:
    """Retrieve ranking SERP results analyzed for this opportunity."""
    opp = await db.get(ContentOpportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    # Find snapshot by primary keyword
    stmt = (
        select(SERPSnapshot)
        .where(SERPSnapshot.query == opp.primary_keyword)
        .order_by(desc(SERPSnapshot.retrieved_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    snap = res.scalar_one_or_none()
    if not snap:
        return ApiResponse(data=[])

    res_stmt = select(SERPResult).where(SERPResult.snapshot_id == snap.id).order_by(SERPResult.position.asc())
    results = list((await db.execute(res_stmt)).scalars().all())
    return ApiResponse(data=[SERPResultResponse.model_validate(r) for r in results])


@router.get("/{opportunity_id}/score", response_model=ApiResponse[dict[str, Any]])
async def get_opportunity_score_breakdown(
    opportunity_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Retrieve detailed mathematical scoring breakdown and penalty deductions."""
    opp = await db.get(ContentOpportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    return ApiResponse(data={
        "opportunity_score": opp.opportunity_score,
        "confidence_score": opp.confidence_score,
        "scoring_profile": opp.scoring_profile,
        "score_breakdown": opp.score_breakdown,
        "penalties_breakdown": opp.penalties_breakdown,
        "score_reasons": opp.score_reasons,
    })


@router.get("/{opportunity_id}/explanation", response_model=ApiResponse[OpportunityExplanationResponse])
async def get_opportunity_explanation(
    opportunity_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[OpportunityExplanationResponse]:
    """Retrieve structured diagnostic explainability report for why this opportunity was scored."""
    opp = await db.get(ContentOpportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    reasons = opp.score_reasons or []
    pos = [r[2:] for r in reasons if r.startswith("+ ")]
    neg = [r[2:] for r in reasons if r.startswith("- ") and not r.startswith("- Penalty")]
    pens = [r for r in reasons if r.startswith("- Penalty")]

    data_sources = ["EventDiscoveryEngine_v2", "ZohraIntentClassifier_v1", "MockSERPProvider"]

    return ApiResponse(data=OpportunityExplanationResponse(
        opportunity_id=opp.id,
        canonical_topic=opp.canonical_topic,
        working_title=opp.working_title,
        recommended_action=ContentAction(opp.recommended_action),
        opportunity_score=opp.opportunity_score,
        confidence_score=opp.confidence_score,
        priority=opp.priority,
        positive_factors=pos,
        negative_factors=neg,
        penalties_applied=pens,
        score_breakdown=opp.score_breakdown or {},
        missing_data_notes=["External search volume and CPC were unavailable (marked NULL, not 0)"],
        risk_notes=opp.risk_flags or [],
        data_sources=data_sources,
    ))


@router.get("/{opportunity_id}/package", response_model=ApiResponse[ContentOpportunityPackage])
async def get_opportunity_handoff_package(
    opportunity_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[ContentOpportunityPackage]:
    """Generates the standardized ContentOpportunityPackage for Part 4 research handoff."""
    stmt = (
        select(ContentOpportunity)
        .options(selectinload(ContentOpportunity.gaps), selectinload(ContentOpportunity.questions))
        .where(ContentOpportunity.id == opportunity_id)
    )
    res = await db.execute(stmt)
    opp = res.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    pkg = build_opportunity_package(opp)
    return ApiResponse(data=pkg)


@router.post("/{opportunity_id}/action", response_model=ApiResponse[ContentOpportunityResponse])
async def override_opportunity_action(
    opportunity_id: UUID,
    payload: ContentActionOverrideRequest,
    token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[ContentOpportunityResponse]:
    """Admin override for recommended action (CREATE vs UPDATE vs EXPAND) with audit logging."""
    opp = await db.get(ContentOpportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    old_action = opp.recommended_action
    opp.recommended_action = payload.recommended_action.value
    if payload.target_content_id:
        opp.target_content_id = payload.target_content_id

    await AuditService.log_action(
        db,
        action="opportunity.override_action",
        resource_type="content_opportunity",
        resource_id=str(opp.id),
        user_id=token.get("sub", "admin"),
        changes={"old_action": old_action, "new_action": opp.recommended_action, "reason": payload.reason},
    )
    await db.commit()
    await db.refresh(opp)
    return ApiResponse(data=ContentOpportunityResponse.model_validate(opp))


@router.post("/{opportunity_id}/status", response_model=ApiResponse[ContentOpportunityResponse])
async def update_opportunity_status(
    opportunity_id: UUID,
    new_status: OpportunityStatus,
    token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[ContentOpportunityResponse]:
    """Admin updates opportunity status (e.g. approve, reject, watch, research_requested)."""
    opp = await db.get(ContentOpportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    old_status = opp.status
    opp.status = new_status.value

    await AuditService.log_action(
        db,
        action="opportunity.update_status",
        resource_type="content_opportunity",
        resource_id=str(opp.id),
        user_id=token.get("sub", "admin"),
        changes={"old_status": old_status, "new_status": new_status.value},
    )
    await db.commit()
    await db.refresh(opp)
    return ApiResponse(data=ContentOpportunityResponse.model_validate(opp))
