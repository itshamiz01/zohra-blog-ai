"""
Zohra — Research Package Builder.

Assembles the immutable, versioned FinalResearchPackage containing verified facts,
safe claim IDs, writer policies, and citation mapping for Part 5.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.schemas.research import (
    FinalResearchPackage,
    ResearchQuestionsSummary,
    VerifiedFactHandoff,
    WriterInstructions,
    WriterPolicy,
)


class ResearchPackageBuilder:
    """Constructs the canonical immutable ResearchPackage handoff object."""

    @classmethod
    def build_package(
        cls,
        project_id: uuid.UUID | str,
        opportunity_id: uuid.UUID | str,
        topic: str,
        research_objective: str,
        claims: Sequence[dict[str, Any]],
        sources: Sequence[dict[str, Any]],
        questions: Sequence[dict[str, Any]],
        contradictions: Sequence[dict[str, Any]],
        timeline_events: Sequence[dict[str, Any]],
        entity_edges: Sequence[dict[str, Any]],
        content_gaps: Sequence[dict[str, Any]],
        quality_result: dict[str, Any],
        risk_flags: Sequence[str] | None = None,
        version: int = 1,
    ) -> FinalResearchPackage:
        now = datetime.now(UTC)

        verified_facts: list[VerifiedFactHandoff] = []
        uncertain_claims: list[dict[str, Any]] = []

        safe_claim_ids: list[str] = []
        attrib_claim_ids: list[str] = []
        do_not_state_ids: list[str] = []
        time_sensitive_ids: list[str] = []

        important_numbers: list[dict[str, Any]] = []
        important_dates: list[dict[str, Any]] = []
        limitations: list[dict[str, Any]] = []
        citation_map: dict[str, list[str]] = {}

        # 1. Process claims and writer instructions
        for c in claims:
            c_id = str(c.get("id") or uuid.uuid4())
            c_text = c.get("claim_text", "")
            c_type = c.get("claim_type", "fact")
            status = c.get("status", "unverified")
            conf = float(c.get("confidence_score", 0.0))
            is_time = bool(c.get("time_sensitive", False))
            is_attrib = bool(c.get("attribution_required", False))
            w_policy = c.get("writer_policy", WriterPolicy.DO_NOT_STATE_AS_FACT.value)
            ev_list = c.get("evidence", [])

            # Build citation map
            src_urls = [ev.get("url") for ev in ev_list if ev.get("url")]
            citation_map[c_id] = src_urls

            if is_time:
                time_sensitive_ids.append(c_id)

            if status in ("strongly_supported", "supported"):
                if is_attrib or w_policy == WriterPolicy.REQUIRE_ATTRIBUTION.value:
                    attrib_claim_ids.append(c_id)
                else:
                    safe_claim_ids.append(c_id)

                verified_facts.append(
                    VerifiedFactHandoff(
                        claim_id=c_id,
                        claim=c_text,
                        claim_type=c_type,
                        subject=c.get("subject"),
                        predicate=c.get("predicate"),
                        object_value=c.get("object_value"),
                        numeric_value=c.get("numeric_value"),
                        unit=c.get("unit"),
                        currency=c.get("currency"),
                        region=c.get("region"),
                        temporal_scope=c.get("temporal_scope"),
                        status=status,
                        confidence=conf,
                        time_sensitive=is_time,
                        attribution_required=is_attrib,
                        writer_policy=w_policy,
                        evidence=ev_list,
                    )
                )
            else:
                do_not_state_ids.append(c_id)
                uncertain_claims.append({
                    "claim_id": c_id,
                    "claim": c_text,
                    "claim_type": c_type,
                    "status": status,
                    "confidence": conf,
                    "reason": "Insufficient independent corroboration or disputed evidence",
                })

            # Segment by domain
            if c_type in ("number", "price") or c.get("numeric_value") is not None:
                important_numbers.append({
                    "claim_id": c_id,
                    "numeric_value": c.get("numeric_value"),
                    "unit": c.get("unit") or c.get("currency"),
                    "context": c_text,
                })
            elif c_type == "date" or c.get("temporal_scope"):
                important_dates.append({
                    "claim_id": c_id,
                    "date_reference": c.get("temporal_scope") or c_text,
                    "context": c_text,
                })
            elif c_type == "limitation":
                limitations.append({
                    "claim_id": c_id,
                    "limitation": c_text,
                })

        # 2. Separate sources into primary vs supporting
        primary_sources: list[dict[str, Any]] = []
        supporting_sources: list[dict[str, Any]] = []

        for s in sources:
            src_clean = {
                "source_id": str(s.get("id")),
                "url": s.get("url"),
                "title": s.get("title"),
                "publisher": s.get("publisher"),
                "source_type": s.get("source_type"),
                "tier": s.get("source_tier"),
                "published_at": s.get("published_at").isoformat() if s.get("published_at") else None,
                "research_value": s.get("research_value_score", 70.0),
            }
            if s.get("is_primary_source") or s.get("is_official_source"):
                primary_sources.append(src_clean)
            else:
                supporting_sources.append(src_clean)

        # 3. Questions summary
        ans_q = [q for q in questions if q.get("status") == "answered"]
        part_q = [q for q in questions if q.get("status") == "partially_answered"]
        unans_q = [q for q in questions if q.get("status") in ("unanswered", "not_found")]

        # 4. Generate executive summary
        summary = (
            f"Autonomous deep research for '{topic}' completed at version {version}. "
            f"Evaluated {len(sources)} sources ({len(primary_sources)} primary) and extracted "
            f"{len(claims)} atomic claims ({len(verified_facts)} verified, {len(uncertain_claims)} uncertain). "
            f"Research Quality Score: {quality_result.get('research_quality_score', 85.0)}/100, "
            f"Confidence: {quality_result.get('research_confidence_score', 85.0)}/100. "
            f"{len(safe_claim_ids)} claims designated as safe for drafting."
        )

        return FinalResearchPackage(
            research_project_id=str(project_id),
            opportunity_id=str(opportunity_id),
            topic=topic,
            research_objective=research_objective,
            executive_summary=summary,
            verified_facts=verified_facts,
            uncertain_claims=uncertain_claims,
            contradictions=[dict(c) for c in contradictions],
            timeline=[dict(t) for t in timeline_events],
            entities=[dict(e) for e in entity_edges],
            primary_sources=primary_sources,
            supporting_sources=supporting_sources,
            research_questions=ResearchQuestionsSummary(
                answered=[dict(q) for q in ans_q],
                partially_answered=[dict(q) for q in part_q],
                unanswered=[dict(q) for q in unans_q],
            ),
            content_gaps=[dict(g) for g in content_gaps],
            important_numbers=important_numbers,
            important_dates=important_dates,
            limitations=limitations,
            risk_flags=list(risk_flags or []),
            research_quality_score=float(quality_result.get("research_quality_score", 0.0)),
            research_confidence_score=float(quality_result.get("research_confidence_score", 0.0)),
            source_quality_score=float(quality_result.get("source_quality_score", 0.0)),
            critical_claim_coverage_score=float(quality_result.get("critical_claim_coverage_score", 0.0)),
            instructions_for_writer=WriterInstructions(
                safe_claim_ids=safe_claim_ids,
                attribution_required_claim_ids=attrib_claim_ids,
                do_not_state_as_fact_claim_ids=do_not_state_ids,
                time_sensitive_claim_ids=time_sensitive_ids,
            ),
            citation_map=citation_map,
            version=version,
            generated_at=now,
        )
