"""
Zohra — Research API Endpoints (Part 4).

REST endpoints for starting research, querying evidence, claims, contradictions,
timeline, source provenance, quality score breakdown, and handoff packages.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_token
from app.db.models.claims import Claim
from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.contradictions import Contradiction
from app.db.models.evidence_items import EvidenceItem
from app.db.models.research_gaps import ResearchGap
from app.db.models.research_packages import ResearchPackage
from app.db.models.research_projects import ResearchProject
from app.db.models.research_questions import ResearchQuestion
from app.db.models.research_sources import ResearchSource
from app.db.models.research_timeline import ResearchTimelineEvent
from app.db.session import get_db
from app.opportunity.handoff import build_opportunity_package
from app.research.pipeline import ResearchPipeline
from app.schemas.research import (
    ClaimResponse,
    ContradictionResolveRequest,
    ContradictionResponse,
    EvidenceItemResponse,
    ResearchGapResponse,
    ResearchProjectCreateRequest,
    ResearchProjectResponse,
    ResearchQuestionResponse,
    ResearchSourceResponse,
    ResearchTimelineResponse,
)

router = APIRouter(prefix="/research", tags=["Research & Evidence"])


@router.post("", response_model=ResearchProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_research_project(
    request: ResearchProjectCreateRequest,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Initiates autonomous deep research for a qualified content opportunity."""
    stmt = select(ContentOpportunity).where(ContentOpportunity.id == request.opportunity_id)
    res = await session.execute(stmt)
    opp = res.scalars().first()

    if not opp:
        raise HTTPException(status_code=404, detail=f"ContentOpportunity {request.opportunity_id} not found")

    pkg = build_opportunity_package(opp)
    pipeline = ResearchPipeline(session)
    final_pkg = await pipeline.run_research(package=pkg, research_depth=request.research_depth)

    # Return updated project
    proj_stmt = select(ResearchProject).where(ResearchProject.id == uuid.UUID(final_pkg.research_project_id))
    proj_res = await session.execute(proj_stmt)
    project = proj_res.scalars().first()
    return project


@router.get("", response_model=list[ResearchProjectResponse])
async def list_research_projects(
    status_filter: str | None = Query(None, alias="status"),
    depth_filter: str | None = Query(None, alias="depth"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists research projects with optional status and depth filtering."""
    query = select(ResearchProject).order_by(desc(ResearchProject.created_at))
    if status_filter:
        query = query.where(ResearchProject.status == status_filter)
    if depth_filter:
        query = query.where(ResearchProject.research_depth == depth_filter.upper())
    query = query.limit(limit).offset(offset)
    res = await session.execute(query)
    return res.scalars().all()


@router.get("/{project_id}", response_model=ResearchProjectResponse)
async def get_research_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Retrieves full details of a specific research project."""
    stmt = select(ResearchProject).where(ResearchProject.id == project_id)
    res = await session.execute(stmt)
    project = res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="ResearchProject not found")
    return project


@router.get("/{project_id}/status")
async def get_research_status(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Returns current execution status and high-level progress indicators."""
    stmt = select(ResearchProject).where(ResearchProject.id == project_id)
    res = await session.execute(stmt)
    project = res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="ResearchProject not found")

    return {
        "project_id": str(project.id),
        "status": project.status,
        "coverage_score": project.coverage_score,
        "research_quality_score": project.research_quality_score,
        "research_confidence_score": project.research_confidence_score,
        "source_count": project.source_count,
        "claim_count": project.claim_count,
        "verified_claim_count": project.verified_claim_count,
        "contradiction_count": project.contradiction_count,
        "stop_reason": project.stop_reason,
    }


@router.get("/{project_id}/questions", response_model=list[ResearchQuestionResponse])
async def get_research_questions(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists all decomposed research questions and their answer status."""
    stmt = select(ResearchQuestion).where(ResearchQuestion.research_project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{project_id}/sources", response_model=list[ResearchSourceResponse])
async def get_research_sources(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists evaluated sources with provenance, tiers, and research value scores."""
    stmt = select(ResearchSource).where(ResearchSource.research_project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{project_id}/claims", response_model=list[ClaimResponse])
async def get_research_claims(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists extracted atomic claims, verification levels, and writer policies."""
    stmt = select(Claim).where(Claim.research_project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{project_id}/evidence", response_model=list[EvidenceItemResponse])
async def get_research_evidence(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists evidence items linking claims to specific source passages."""
    stmt = (
        select(EvidenceItem)
        .join(Claim, EvidenceItem.claim_id == Claim.id)
        .where(Claim.research_project_id == project_id)
    )
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{project_id}/contradictions", response_model=list[ContradictionResponse])
async def get_research_contradictions(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists detected factual disagreements and resolution statuses."""
    stmt = select(Contradiction).where(Contradiction.research_project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{project_id}/timeline", response_model=list[ResearchTimelineResponse])
async def get_research_timeline(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists chronological timeline events with temporal precision."""
    stmt = (
        select(ResearchTimelineEvent)
        .where(ResearchTimelineEvent.research_project_id == project_id)
        .order_by(ResearchTimelineEvent.event_time)
    )
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{project_id}/gaps", response_model=list[ResearchGapResponse])
async def get_research_gaps(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists open or investigated research gaps."""
    stmt = select(ResearchGap).where(ResearchGap.research_project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{project_id}/package")
async def get_final_research_package(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Retrieves the immutable, versioned FinalResearchPackage for Part 5 handoff."""
    stmt = (
        select(ResearchPackage)
        .where(ResearchPackage.research_project_id == project_id)
        .order_by(desc(ResearchPackage.version))
    )
    res = await session.execute(stmt)
    pkg = res.scalars().first()
    if not pkg:
        raise HTTPException(status_code=404, detail="ResearchPackage not found for this project")

    return {
        "research_project_id": str(pkg.research_project_id),
        "opportunity_id": str(pkg.opportunity_id),
        "version": pkg.version,
        "topic": pkg.topic,
        "research_objective": pkg.research_objective,
        "executive_summary": pkg.executive_summary,
        "verified_facts": pkg.verified_facts_json,
        "uncertain_claims": pkg.uncertain_claims_json,
        "contradictions": pkg.contradictions_json,
        "timeline": pkg.timeline_json,
        "entities": pkg.entities_json,
        "primary_sources": pkg.primary_sources_json,
        "supporting_sources": pkg.supporting_sources_json,
        "research_questions": {
            "answered": pkg.questions_answered_json or [],
            "unanswered": pkg.questions_unanswered_json or [],
        },
        "content_gaps": pkg.content_gaps_json,
        "important_numbers": pkg.important_numbers_json,
        "important_dates": pkg.important_dates_json,
        "limitations": pkg.limitations_json,
        "risk_flags": pkg.risk_flags_json,
        "research_quality_score": pkg.research_quality_score,
        "research_confidence_score": pkg.research_confidence_score,
        "source_quality_score": pkg.source_quality_score,
        "critical_claim_coverage_score": pkg.critical_claim_coverage_score,
        "instructions_for_writer": pkg.instructions_for_writer_json,
        "citation_map": pkg.citation_map_json,
        "generated_at": pkg.generated_at.isoformat(),
    }


@router.get("/{project_id}/explanation")
async def get_research_explanation(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Provides auditable rationale for research results, quality score, and evidence verification."""
    stmt = select(ResearchProject).where(ResearchProject.id == project_id)
    res = await session.execute(stmt)
    project = res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="ResearchProject not found")

    return {
        "project_id": str(project.id),
        "topic": project.topic,
        "research_depth": project.research_depth,
        "coverage_score": project.coverage_score,
        "critical_claim_coverage": project.critical_claim_coverage_score,
        "source_quality_score": project.source_quality_score,
        "research_quality_score": project.research_quality_score,
        "research_confidence_score": project.research_confidence_score,
        "sources_evaluated": project.source_count,
        "primary_sources": project.primary_source_count,
        "claims_extracted": project.claim_count,
        "claims_verified": project.verified_claim_count,
        "contradictions_detected": project.contradiction_count,
        "stop_reason": project.stop_reason,
        "status": project.status,
    }


@router.post("/{project_id}/resolve-contradiction")
async def resolve_contradiction_admin(
    project_id: uuid.UUID,
    contradiction_id: uuid.UUID,
    request: ContradictionResolveRequest,
    session: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin_token),
):
    """Admin manual override to resolve a disputed factual contradiction."""
    stmt = select(Contradiction).where(
        Contradiction.id == contradiction_id,
        Contradiction.research_project_id == project_id,
    )
    res = await session.execute(stmt)
    contra = res.scalars().first()
    if not contra:
        raise HTTPException(status_code=404, detail="Contradiction not found")

    contra.resolution_status = request.resolution_status.value
    contra.resolution_reason = request.resolution_reason
    contra.preferred_claim_id = request.preferred_claim_id
    await session.commit()
    return {"message": "Contradiction resolved", "id": str(contra.id), "status": contra.resolution_status}
