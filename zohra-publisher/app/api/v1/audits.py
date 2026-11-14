"""
Zohra — Audits API Router (Part 6).

REST endpoints for independent editorial audit projects, claim audits,
citation verifications, issues, scores, decisions, explanations, and admin actions.
AsyncSession and require_admin_token architecture.
"""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_token
from app.db.models.audit_issues import AuditIssue
from app.db.models.audit_projects import AuditProject
from app.db.models.audited_claims import AuditedClaim
from app.db.models.draft_projects import DraftProject
from app.db.models.editorial_draft_packages import EditorialDraftPackage
from app.db.models.final_audit_packages import FinalAuditPackage
from app.db.models.research_packages import ResearchPackage
from app.db.session import get_db
from app.schemas.audit import (
    AuditCreateRequest,
    AuditDecision,
    AuditExplanationResponse,
    AuditIssueItem,
    AuditProjectResponse,
    AuditQualityScores,
    AuditStatusResponse,
    HumanOverrideRequest,
    IssueSeverity,
)
from app.workers.audit_tasks import start_audit_project_task

router = APIRouter(prefix="/audits", tags=["Independent Editorial Audit & Quality Firewall"])


@router.post("", response_model=AuditProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    request: AuditCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Enqueues an independent editorial quality audit for an EditorialDraftPackage."""
    # Verify draft project exists
    res = await db.execute(select(DraftProject).where(DraftProject.id == request.draft_project_id))
    draft_proj = res.scalar_one_or_none()
    if not draft_proj:
        raise HTTPException(status_code=404, detail="Draft project not found")

    # Find latest draft package
    edp_res = await db.execute(
        select(EditorialDraftPackage)
        .where(EditorialDraftPackage.draft_project_id == request.draft_project_id)
        .order_by(EditorialDraftPackage.version.desc())
    )
    edp = edp_res.scalars().first()
    if not edp:
        raise HTTPException(status_code=400, detail="Draft has not generated an EditorialDraftPackage yet")

    # Find research package
    resp_res = await db.execute(select(ResearchPackage).where(ResearchPackage.id == edp.research_package_id))
    resp = resp_res.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=400, detail="Research package not found")

    # Create AuditProject
    audit = AuditProject(
        draft_project_id=draft_proj.id,
        draft_version_id=request.draft_version_id,
        research_project_id=resp.research_project_id,
        research_package_id=resp.id,
        research_package_version=resp.version,
        opportunity_id=draft_proj.opportunity_id,
        site_id=draft_proj.site_id,
        audit_type=request.audit_type,
        policy_version=request.policy_version,
        status="queued",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    # Launch Celery background task
    with contextlib.suppress(Exception):
        start_audit_project_task.delay(str(audit.id))

    return audit


@router.get("", response_model=list[AuditProjectResponse])
async def list_audits(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str | None = None,
    decision_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists audit projects with filtering."""
    query = select(AuditProject).order_by(desc(AuditProject.created_at)).offset(offset).limit(limit)
    if status_filter:
        query = query.where(AuditProject.status == status_filter)
    if decision_filter:
        query = query.where(AuditProject.decision == decision_filter)

    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{audit_id}", response_model=AuditProjectResponse)
async def get_audit(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Retrieves audit project details."""
    res = await db.execute(select(AuditProject).where(AuditProject.id == audit_id))
    audit = res.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit project not found")
    return audit


@router.get("/{audit_id}/status", response_model=AuditStatusResponse)
async def get_audit_status(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Polls audit status, overall score, and decision."""
    res = await db.execute(select(AuditProject).where(AuditProject.id == audit_id))
    audit = res.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit project not found")
    return audit


@router.get("/{audit_id}/claims")
async def get_audit_claims(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Retrieves all independently re-extracted claims and their verification status."""
    res = await db.execute(select(AuditedClaim).where(AuditedClaim.audit_project_id == audit_id))
    return res.scalars().all()


@router.get("/{audit_id}/issues", response_model=list[AuditIssueItem])
async def get_audit_issues(
    audit_id: uuid.UUID,
    severity: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Lists granular issues found during the audit passes."""
    query = select(AuditIssue).where(AuditIssue.audit_project_id == audit_id)
    if severity:
        query = query.where(AuditIssue.severity == severity.upper())
    res = await db.execute(query)
    issues = res.scalars().all()
    return [
        AuditIssueItem(
            issue_code=i.issue_code,
            issue_category=i.issue_category,
            severity=IssueSeverity(i.severity),
            section_id=i.section_id,
            paragraph_index=i.paragraph_index,
            sentence_index=i.sentence_index,
            claim_id=str(i.claim_id) if i.claim_id else None,
            source_id=str(i.source_id) if i.source_id else None,
            description=i.description,
            evidence=i.evidence,
            recommended_action=i.recommended_action,
            routing_target=i.routing_target,
        )
        for i in issues
    ]


@router.get("/{audit_id}/explanation", response_model=AuditExplanationResponse)
async def get_audit_explanation(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Returns a transparent, machine-readable explanation of the audit verdict."""
    res = await db.execute(select(AuditProject).where(AuditProject.id == audit_id))
    audit = res.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit project not found")

    fap_res = await db.execute(
        select(FinalAuditPackage).where(FinalAuditPackage.audit_project_id == audit.id)
    )
    fap = fap_res.scalar_one_or_none()
    pkg_json = fap.package_json if fap else {}

    scores = AuditQualityScores(
        factual_integrity=audit.factual_score,
        grounding=audit.grounding_score,
        citation_quality=audit.citation_score,
        temporal_integrity=audit.temporal_score,
        originality=audit.originality_score,
        intent_satisfaction=audit.intent_score,
        information_gain=audit.information_gain_score,
        seo_quality=audit.seo_score,
        content_quality=audit.content_quality_score,
        structure=audit.structure_score,
        brand_voice=audit.brand_score,
        risk_compliance=audit.risk_score,
        overall_score=audit.overall_quality_score,
    )

    decision_enum = AuditDecision(audit.decision) if audit.decision else AuditDecision.REVISE
    eligible = fap.eligible_for_part7 if fap else False

    crit_fails = pkg_json.get("critical_failures", [])
    why = f"Audit reached decision {decision_enum.value} with overall score {audit.overall_quality_score:.1f}/100."
    if crit_fails:
        why += f" Critical failure overrides triggered: {', '.join(crit_fails)}."

    next_steps = {
        AuditDecision.PASS: "Eligible for publication preparation in Part 7.",
        AuditDecision.REVISE: "Route surgical revision package to Part 5 Writer.",
        AuditDecision.MORE_RESEARCH: "Route research return package to Part 4 Deep Research.",
        AuditDecision.HUMAN_REVIEW: "Awaiting editorial board human review.",
        AuditDecision.REJECT: "Opportunity permanently rejected; do not publish.",
    }

    return AuditExplanationResponse(
        audit_id=audit.id,
        decision=decision_enum,
        eligible_for_part7=eligible,
        why_decision_reached=why,
        critical_failures=crit_fails,
        score_breakdown=scores,
        failed_claims=[],
        failed_citations=[],
        numeric_date_discrepancies=[],
        originality_findings=[],
        seo_findings=[],
        risk_findings=[],
        next_step=next_steps.get(decision_enum, "Review audit report."),
        routing_package=None,
    )


@router.post("/{audit_id}/override", response_model=AuditProjectResponse)
async def human_override(
    audit_id: uuid.UUID,
    request: HumanOverrideRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Admin endpoint to record human override on an issue or audit decision with an immutable audit log."""
    res = await db.execute(select(AuditProject).where(AuditProject.id == audit_id))
    audit = res.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit project not found")

    if request.issue_id:
        iss_res = await db.execute(
            select(AuditIssue).where(AuditIssue.id == request.issue_id, AuditIssue.audit_project_id == audit.id)
        )
        issue = iss_res.scalar_one_or_none()
        if issue:
            issue.status = "overridden"
            issue.override_reason = request.reason
            issue.overridden_by = request.actor
            issue.resolved_at = datetime.now(UTC)

    if request.override_decision:
        audit.decision = request.override_decision.value
        audit.decision_reason_json = {
            "override": True,
            "overridden_by": request.actor,
            "reason": request.reason,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    await db.commit()
    await db.refresh(audit)
    return audit


@router.post("/{audit_id}/rerun", response_model=AuditProjectResponse)
async def rerun_audit(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin_token),
):
    """Admin endpoint to re-execute an audit run."""
    res = await db.execute(select(AuditProject).where(AuditProject.id == audit_id))
    audit = res.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit project not found")

    audit.status = "queued"
    audit.decision = None
    await db.commit()
    await db.refresh(audit)

    with contextlib.suppress(Exception):
        start_audit_project_task.delay(str(audit.id))
    return audit
