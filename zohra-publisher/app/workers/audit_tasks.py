"""
Zohra — Celery Background Tasks for Audit & Quality Firewall (Part 6).

Asynchronous workers for independent editorial audit, claim verification,
and publication firewall decisioning with distributed locking.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.audit.pipeline import AuditPipeline
from app.core.logging import get_logger
from app.db.models.audit_issues import AuditIssue
from app.db.models.audit_projects import AuditProject
from app.db.models.audited_claims import AuditedClaim
from app.db.models.editorial_draft_packages import EditorialDraftPackage
from app.db.models.final_audit_packages import FinalAuditPackage
from app.db.models.research_packages import ResearchPackage
from app.db.session import async_session_factory
from app.utils.redis import distributed_lock
from app.workers.celery_app import celery_app

logger = get_logger("workers.audit")


@celery_app.task(name="audit.start_project", bind=True, max_retries=2, default_retry_delay=30)
def start_audit_project_task(self, audit_project_id_str: str) -> dict:
    """Runs full independent audit pipeline asynchronously for an AuditProject."""
    audit_id = uuid.UUID(audit_project_id_str)
    lock_resource = f"audit:project:{audit_id}"

    with distributed_lock(lock_resource, ttl_seconds=300):
        async def _run():
            async with async_session_factory() as session:
                res = await session.execute(select(AuditProject).where(AuditProject.id == audit_id))
                audit = res.scalar_one_or_none()

                if not audit:
                    logger.error(f"Audit project {audit_id} not found.")
                    return {"status": "error", "message": "Audit project not found"}

                audit.status = "validating"
                audit.started_at = datetime.now(UTC)
                await session.commit()

                # Retrieve draft package
                edp_res = await session.execute(
                    select(EditorialDraftPackage)
                    .where(EditorialDraftPackage.draft_project_id == audit.draft_project_id)
                    .order_by(EditorialDraftPackage.version.desc())
                )
                edp = edp_res.scalars().first()

                # Retrieve research package
                resp_res = await session.execute(
                    select(ResearchPackage).where(ResearchPackage.id == audit.research_package_id)
                )
                resp = resp_res.scalar_one_or_none()

                if not edp or not resp:
                    audit.status = "failed"
                    await session.commit()
                    return {"status": "error", "message": "Missing draft or research package"}

                # Run audit pipeline
                pipeline = AuditPipeline()
                try:
                    final_pkg, issues, claims, rev_pkg, res_pkg, hr_pkg = pipeline.run_audit(
                        editorial_package_json=edp.package_json,
                        research_package_json={
                            "topic": resp.topic,
                            "verified_facts_json": resp.verified_facts_json,
                            "uncertain_claims_json": resp.uncertain_claims_json,
                            "contradictions_json": resp.contradictions_json,
                            "timeline_json": resp.timeline_json,
                            "primary_sources_json": resp.primary_sources_json,
                            "supporting_sources_json": resp.supporting_sources_json,
                            "important_numbers_json": resp.important_numbers_json,
                            "important_dates_json": resp.important_dates_json,
                            "content_gaps_json": resp.content_gaps_json,
                            "questions_answered_json": resp.questions_answered_json,
                            "metadata_json": resp.metadata_json,
                        },
                        draft_project_id=str(audit.draft_project_id),
                        research_package_id=str(audit.research_package_id),
                        opportunity_id=str(audit.opportunity_id),
                        site_id=str(audit.site_id),
                        draft_version_number=edp.version,
                        research_package_version=resp.version,
                        audit_id=str(audit.id),
                    )

                    # Persist issues
                    crit_count = 0
                    maj_count = 0
                    min_count = 0
                    for iss in issues:
                        if iss.severity.value == "CRITICAL":
                            crit_count += 1
                        elif iss.severity.value == "MAJOR":
                            maj_count += 1
                        else:
                            min_count += 1

                        db_issue = AuditIssue(
                            audit_project_id=audit.id,
                            issue_code=iss.issue_code,
                            issue_category=iss.issue_category,
                            severity=iss.severity.value,
                            section_id=iss.section_id,
                            paragraph_index=iss.paragraph_index,
                            sentence_index=iss.sentence_index,
                            description=iss.description,
                            evidence=iss.evidence,
                            recommended_action=iss.recommended_action,
                            routing_target=iss.routing_target,
                        )
                        session.add(db_issue)

                    # Persist claims
                    for clm in claims:
                        db_claim = AuditedClaim(
                            audit_project_id=audit.id,
                            section_id=clm.section_id,
                            sentence_index=clm.sentence_index,
                            claim_text=clm.claim_text,
                            normalized_claim=clm.normalized_claim,
                            importance=clm.importance,
                            matched_research_claim_id=clm.matched_research_claim_id,
                            match_confidence=clm.match_confidence,
                            verification_status=clm.verification_status.value,
                            entailment_score=clm.entailment_score,
                            audit_notes=clm.audit_notes,
                        )
                        session.add(db_claim)

                    # Update AuditProject
                    audit.status = "completed"
                    audit.decision = final_pkg.decision.value
                    audit.decision_reason_json = {"reasons": final_pkg.critical_failures or [final_pkg.decision.value]}
                    audit.overall_quality_score = final_pkg.scores.overall_score
                    audit.factual_score = final_pkg.scores.factual_integrity
                    audit.grounding_score = final_pkg.scores.grounding
                    audit.citation_score = final_pkg.scores.citation_quality
                    audit.temporal_score = final_pkg.scores.temporal_integrity
                    audit.originality_score = final_pkg.scores.originality
                    audit.intent_score = final_pkg.scores.intent_satisfaction
                    audit.information_gain_score = final_pkg.scores.information_gain
                    audit.seo_score = final_pkg.scores.seo_quality
                    audit.content_quality_score = final_pkg.scores.content_quality
                    audit.structure_score = final_pkg.scores.structure
                    audit.brand_score = final_pkg.scores.brand_voice
                    audit.risk_score = final_pkg.scores.risk_compliance
                    audit.critical_issue_count = crit_count
                    audit.major_issue_count = maj_count
                    audit.minor_issue_count = min_count
                    audit.content_hash = final_pkg.content_hash
                    audit.audit_fingerprint = final_pkg.audit_fingerprint
                    audit.completed_at = datetime.now(UTC)

                    # Persist FinalAuditPackage
                    final_record = FinalAuditPackage(
                        audit_project_id=audit.id,
                        draft_project_id=audit.draft_project_id,
                        draft_version_number=edp.version,
                        research_package_id=audit.research_package_id,
                        research_package_version=resp.version,
                        decision=final_pkg.decision.value,
                        eligible_for_part7=final_pkg.eligible_for_part7,
                        overall_quality_score=final_pkg.scores.overall_score,
                        factual_score=final_pkg.scores.factual_integrity,
                        grounding_score=final_pkg.scores.grounding,
                        content_hash=final_pkg.content_hash,
                        audit_fingerprint=final_pkg.audit_fingerprint,
                        audit_token=final_pkg.audit_token,
                        package_json=final_pkg.model_dump(),
                        completed_at=datetime.now(UTC),
                    )
                    session.add(final_record)
                    await session.commit()

                    return {
                        "audit_project_id": str(audit.id),
                        "decision": final_pkg.decision.value,
                        "overall_score": final_pkg.scores.overall_score,
                        "eligible_for_part7": final_pkg.eligible_for_part7,
                    }
                except Exception as exc:
                    logger.error(f"Audit execution error: {exc}", exc_info=True)
                    audit.status = "failed"
                    await session.commit()
                    raise

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        except Exception as exc:
            raise self.retry(exc=exc, countdown=10) from exc
        finally:
            loop.close()
