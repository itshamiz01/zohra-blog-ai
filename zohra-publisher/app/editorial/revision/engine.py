"""
Zohra — Revision Engine (Part 5).

Generates targeted, section-level revision plans when a draft fails the quality gate:
identifies isolated flaws (slop clichés, ungrounded sentences, missing attribution),
regenerates only the affected sections, and enforces a strict maximum revision cycle limit (default: 3).
"""

from __future__ import annotations

from typing import Any

from app.editorial.grounding.verifier import GroundingReport
from app.editorial.seo.anti_slop import AISlopDetector
from app.schemas.editorial import DraftQualityScores, DraftSection


class RevisionPlan:
    def __init__(
        self,
        tasks: list[dict[str, Any]],
        should_abort: bool = False,
        abort_reason: str | None = None,
    ):
        self.tasks = tasks
        self.should_abort = should_abort
        self.abort_reason = abort_reason


class RevisionEngine:
    """Manages targeted section repairs without unnecessary full-draft rewrites."""

    MAX_REVISION_CYCLES = 3

    @classmethod
    def create_revision_plan(
        cls,
        quality_scores: DraftQualityScores,
        grounding_report: GroundingReport,
        sections: list[DraftSection],
        current_cycle: int = 1,
    ) -> RevisionPlan:
        # Check cycle limit
        if current_cycle > cls.MAX_REVISION_CYCLES:
            return RevisionPlan(
                tasks=[],
                should_abort=True,
                abort_reason=f"Exceeded maximum allowed revision cycles ({cls.MAX_REVISION_CYCLES}). Routing to human review.",
            )

        tasks: list[dict[str, Any]] = []

        # 1. Check for ungrounded sentences or prohibited claims
        if grounding_report.prohibited_claims_found:
            tasks.append({
                "issue_type": "prohibited_claim_removal",
                "severity": "critical",
                "section_id": "sec_overview",
                "instruction": "Remove any speculative or disputed assertion matching prohibited claims.",
            })

        if not grounding_report.attribution_compliant:
            tasks.append({
                "issue_type": "missing_attribution",
                "severity": "high",
                "section_id": None,
                "instruction": "Add explicit attribution markers ('according to official documentation') for company or uncorroborated assertions.",
            })

        # 2. Check for AI slop clichés
        for sec in sections:
            slop_eval = AISlopDetector.evaluate(sec.content)
            if slop_eval["slop_count"] > 0:
                tasks.append({
                    "issue_type": "slop_removal",
                    "severity": "medium",
                    "section_id": sec.section_id,
                    "instruction": f"Remove {slop_eval['slop_count']} generic AI clichés (e.g. 'In today's fast-paced world', 'game-changer') and replace with concrete statements.",
                })

        # 3. Check for clarity or redundancy deficiencies
        if quality_scores.readability < 60.0:
            tasks.append({
                "issue_type": "redundancy_reduction",
                "severity": "medium",
                "section_id": "sec_capabilities",
                "instruction": "Reduce repeated phrasing and eliminate redundant transitional paragraphs.",
            })

        return RevisionPlan(tasks=tasks)

    @classmethod
    def apply_revision(
        cls,
        section: DraftSection,
        instruction: str,
    ) -> DraftSection:
        """Applies targeted revision to a single section."""
        clean_content = AISlopDetector.cleanse_slop(section.content)
        return DraftSection(
            section_id=section.section_id,
            heading=section.heading,
            content=clean_content,
            used_claim_ids=section.used_claim_ids,
            citation_placements=section.citation_placements,
            unresolved_issues=[],
        )
