"""
Zohra — Reddit Opportunity & Referral Engine API Endpoints.

Provides administrative controls, question inspection, cluster visualization,
approval queue management, dry-run simulation, and referral analytics.
"""

from __future__ import annotations

from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import require_admin_token
from app.db.models.reddit import (
    RedditCommunityPolicy,
    RedditOpportunity,
    RedditQuestion,
    RedditQuestionCluster,
    RedditResponseDraft,
)
from app.db.session import get_db
from app.reddit.service import RedditEngineService
from app.schemas.api import ApiResponse

router = APIRouter(prefix="/reddit", tags=["Reddit Engine"])


@router.get("/status", response_model=ApiResponse[dict[str, Any]])
async def get_reddit_engine_status(
    _token: Annotated[dict, Depends(require_admin_token)],
) -> ApiResponse[dict[str, Any]]:
    """Returns operational status, safety gates, and configuration for Reddit Engine."""
    settings = get_settings()
    data = {
        "reddit_enabled": getattr(settings, "REDDIT_ENABLED", False),
        "discovery_enabled": getattr(settings, "REDDIT_DISCOVERY_ENABLED", True),
        "response_generation_enabled": getattr(settings, "REDDIT_RESPONSE_GENERATION_ENABLED", False),
        "posting_enabled": getattr(settings, "REDDIT_POSTING_ENABLED", False),
        "autonomy_mode": getattr(settings, "REDDIT_AUTONOMY_MODE", "DISCOVERY_ONLY"),
        "monitored_subreddits": getattr(settings, "REDDIT_MONITORED_SUBREDDITS", []),
        "daily_comment_limit": getattr(settings, "REDDIT_MAX_COMMENTS_PER_DAY", 5),
        "min_opportunity_score": getattr(settings, "REDDIT_MIN_OPPORTUNITY_SCORE", 65.0),
        "oauth_configured": bool(getattr(settings, "REDDIT_CLIENT_ID", None)),
    }
    return ApiResponse(success=True, data=data)


@router.get("/overview", response_model=ApiResponse[dict[str, Any]])
async def get_reddit_overview_metrics(
    site_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Returns aggregated high-level metrics for the Reddit Intelligence dashboard."""
    from sqlalchemy import func
    from app.db.models.reddit import RedditPublication, RedditReferralEvent

    # Questions total & today
    total_q = (await db.execute(
        select(func.count()).select_from(RedditQuestion).where(RedditQuestion.site_id == site_id)
    )).scalar_one() or 0

    # Clusters
    total_clusters = (await db.execute(
        select(func.count()).select_from(RedditQuestionCluster).where(RedditQuestionCluster.site_id == site_id)
    )).scalar_one() or 0

    # Opportunities total & qualified (>= 65)
    total_opps = (await db.execute(
        select(func.count()).select_from(RedditOpportunity).where(RedditOpportunity.site_id == site_id)
    )).scalar_one() or 0

    qualified_opps = (await db.execute(
        select(func.count()).select_from(RedditOpportunity).where(
            RedditOpportunity.site_id == site_id,
            RedditOpportunity.overall_opportunity_score >= 65.0,
        )
    )).scalar_one() or 0

    # Response Drafts
    pending_drafts = (await db.execute(
        select(func.count()).select_from(RedditResponseDraft).where(
            RedditResponseDraft.site_id == site_id,
            RedditResponseDraft.status == "DRAFT_PENDING_APPROVAL",
        )
    )).scalar_one() or 0

    approved_drafts = (await db.execute(
        select(func.count()).select_from(RedditResponseDraft).where(
            RedditResponseDraft.site_id == site_id,
            RedditResponseDraft.status.in_(["APPROVED", "READY_TO_POST"]),
        )
    )).scalar_one() or 0

    # Publications
    published_responses = (await db.execute(
        select(func.count()).select_from(RedditPublication).where(
            RedditPublication.site_id == site_id,
            RedditPublication.status == "PUBLISHED",
        )
    )).scalar_one() or 0

    # Referrals
    referral_events = (await db.execute(
        select(func.count()).select_from(RedditReferralEvent).where(
            RedditReferralEvent.site_id == site_id
        )
    )).scalar_one() or 0

    return ApiResponse(
        success=True,
        data={
            "questions_total": total_q,
            "clusters_total": total_clusters,
            "opportunities_total": total_opps,
            "qualified_opportunities": qualified_opps,
            "pending_drafts": pending_drafts,
            "approved_drafts": approved_drafts,
            "published_responses": published_responses,
            "referral_events_total": referral_events,
        },
    )


@router.get("/policies", response_model=ApiResponse[list[dict[str, Any]]])
async def list_community_policies(
    site_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[dict[str, Any]]]:
    """Lists community rules and posting policies for tracked subreddits."""
    stmt = select(RedditCommunityPolicy).where(
        RedditCommunityPolicy.site_id == site_id
    ).order_by(RedditCommunityPolicy.subreddit.asc())
    res = await db.execute(stmt)
    policies = res.scalars().all()

    data = [
        {
            "id": str(p.id),
            "subreddit": p.subreddit,
            "posting_allowed": p.posting_allowed,
            "commenting_allowed": p.commenting_allowed,
            "external_links_allowed": p.external_links_allowed,
            "self_promotion_allowed": p.self_promotion_allowed,
            "disclosure_required": p.disclosure_required,
            "confidence_level": p.confidence_level,
            "last_checked_at": p.last_checked_at.isoformat() if p.last_checked_at else None,
            "rules_text": p.rules_text,
        }
        for p in policies
    ]
    return ApiResponse(success=True, data=data)


@router.post("/scan", response_model=ApiResponse[dict[str, Any]])
async def trigger_reddit_scan(
    site_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    subreddits: list[str] | None = None,
    limit_per_sub: int = Query(15, ge=1, le=50),
) -> ApiResponse[dict[str, Any]]:
    """Triggers an on-demand scan of monitored subreddits."""
    service = RedditEngineService(db)
    questions = await service.run_discovery_cycle(
        site_id=site_id,
        subreddits=subreddits,
        limit_per_sub=limit_per_sub,
    )
    # Auto-cluster & score
    opps = await service.cluster_and_score_pending_questions(site_id=site_id)

    return ApiResponse(
        success=True,
        data={
            "questions_discovered": len(questions),
            "opportunities_evaluated": len(opps),
            "message": f"Scan completed: {len(questions)} questions found, {len(opps)} opportunities scored.",
        },
    )


@router.get("/questions", response_model=ApiResponse[list[dict[str, Any]]])
async def list_reddit_questions(
    site_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    subreddit: str | None = None,
    limit: int = Query(50, ge=1, le=100),
) -> ApiResponse[list[dict[str, Any]]]:
    """Lists discovered Reddit questions."""
    stmt = select(RedditQuestion).where(RedditQuestion.site_id == site_id)
    if subreddit:
        stmt = stmt.where(RedditQuestion.subreddit == subreddit.lower())
    stmt = stmt.order_by(RedditQuestion.created_at.desc()).limit(limit)

    res = await db.execute(stmt)
    questions = res.scalars().all()

    data = [
        {
            "id": str(q.id),
            "reddit_post_id": q.reddit_post_id,
            "subreddit": q.subreddit,
            "title": q.raw_title,
            "primary_question": q.primary_question,
            "underlying_problem": q.underlying_problem,
            "question_type": q.question_type,
            "search_intent": q.search_intent,
            "relevance_score": q.relevance_score,
            "status": q.status,
            "created_at": q.created_at.isoformat(),
        }
        for q in questions
    ]
    return ApiResponse(success=True, data=data)


@router.get("/clusters", response_model=ApiResponse[list[dict[str, Any]]])
async def list_reddit_clusters(
    site_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[dict[str, Any]]]:
    """Lists thematic question clusters."""
    stmt = select(RedditQuestionCluster).where(
        RedditQuestionCluster.site_id == site_id
    ).order_by(RedditQuestionCluster.question_count.desc())
    res = await db.execute(stmt)
    clusters = res.scalars().all()

    data = [
        {
            "id": str(c.id),
            "cluster_name": c.cluster_name,
            "parent_topic": c.parent_topic,
            "canonical_problem": c.canonical_problem,
            "subtopics": c.subtopics,
            "question_count": c.question_count,
            "momentum_score": c.aggregate_momentum_score,
        }
        for c in clusters
    ]
    return ApiResponse(success=True, data=data)


@router.get("/opportunities", response_model=ApiResponse[list[dict[str, Any]]])
async def list_reddit_opportunities(
    site_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    limit: int = Query(50, ge=1, le=100),
) -> ApiResponse[list[dict[str, Any]]]:
    """Lists scored content opportunities."""
    stmt = select(RedditOpportunity).where(
        RedditOpportunity.site_id == site_id,
        RedditOpportunity.overall_opportunity_score >= min_score,
    ).order_by(RedditOpportunity.overall_opportunity_score.desc()).limit(limit)

    res = await db.execute(stmt)
    opps = res.scalars().all()

    data = [
        {
            "id": str(o.id),
            "working_title": o.working_title,
            "proposed_angle": o.proposed_angle,
            "target_keyword": o.target_keyword,
            "recommended_action": o.recommended_action,
            "opportunity_score": o.overall_opportunity_score,
            "existing_article_match": o.existing_article_title,
            "score_reasons": o.score_reasons,
            "status": o.status,
        }
        for o in opps
    ]
    return ApiResponse(success=True, data=data)


@router.get("/drafts", response_model=ApiResponse[list[dict[str, Any]]])
async def list_response_drafts(
    site_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[dict[str, Any]]]:
    """Lists pending response drafts in the approval queue."""
    service = RedditEngineService(db)
    drafts = await service.approval_mgr.list_pending_drafts(site_id=site_id)

    data = [
        {
            "id": str(d.id),
            "reddit_post_id": d.reddit_post_id,
            "subreddit": d.subreddit,
            "response_type": d.response_type,
            "response_body": d.response_body,
            "has_external_link": d.has_external_link,
            "proposed_link": d.proposed_link,
            "rule_check_passed": d.rule_check_passed,
            "anti_spam_passed": d.anti_spam_passed,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
        }
        for d in drafts
    ]
    return ApiResponse(success=True, data=data)


@router.post("/drafts/{draft_id}/approve", response_model=ApiResponse[dict[str, Any]])
async def approve_response_draft(
    draft_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    strip_link: bool = False,
    custom_body: str | None = None,
) -> ApiResponse[dict[str, Any]]:
    """Approves a response draft in the queue (supports stripping links)."""
    service = RedditEngineService(db)
    draft = await service.approval_mgr.approve_draft(
        draft_id=draft_id,
        reviewed_by=_token.get("sub", "admin"),
        strip_link=strip_link,
        custom_body=custom_body,
    )
    return ApiResponse(
        success=True,
        data={
            "id": str(draft.id),
            "status": draft.status,
            "has_link": draft.has_external_link,
            "message": "Draft successfully approved.",
        },
    )


@router.post("/drafts/{draft_id}/reject", response_model=ApiResponse[dict[str, Any]])
async def reject_response_draft(
    draft_id: uuid.UUID,
    reason: str,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Rejects a response draft."""
    service = RedditEngineService(db)
    draft = await service.approval_mgr.reject_draft(
        draft_id=draft_id,
        reason=reason,
        reviewed_by=_token.get("sub", "admin"),
    )
    return ApiResponse(
        success=True,
        data={
            "id": str(draft.id),
            "status": draft.status,
            "message": "Draft rejected.",
        },
    )


@router.get("/referrals", response_model=ApiResponse[dict[str, Any]])
async def get_reddit_referral_analytics(
    site_id: uuid.UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365),
) -> ApiResponse[dict[str, Any]]:
    """Returns referral analytics summary for Reddit."""
    service = RedditEngineService(db)
    summary = await service.referral_tracker.get_referral_summary(site_id=site_id, days=days)
    return ApiResponse(success=True, data=summary)


@router.post("/dry-run", response_model=ApiResponse[dict[str, Any]])
async def execute_reddit_dry_run(
    site_id: uuid.UUID,
    sample_title: str,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    sample_body: str | None = None,
    subreddit: str = "education",
) -> ApiResponse[dict[str, Any]]:
    """Executes a full end-to-end dry-run without posting to Reddit."""
    service = RedditEngineService(db)
    result = await service.execute_dry_run(
        site_id=site_id,
        sample_title=sample_title,
        sample_body=sample_body,
        subreddit=subreddit,
    )
    return ApiResponse(success=True, data=result)
