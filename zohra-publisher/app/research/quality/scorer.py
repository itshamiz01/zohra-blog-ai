"""
Zohra — Research Quality & Confidence Scorer.

Computes the research quality formula with positive components and explicit penalties,
evaluates confidence, and enforces quality gates (standard vs high-risk YMYL).
"""

from __future__ import annotations

from typing import Any


class QualityEvaluationResult:
    def __init__(
        self,
        research_quality_score: float,
        research_confidence_score: float,
        coverage_score: float,
        critical_claim_coverage_score: float,
        source_quality_score: float,
        primary_source_coverage: float,
        corroboration_score: float,
        freshness_score: float,
        contradiction_resolution_score: float,
        evidence_specificity_score: float,
        total_penalties: float,
        quality_gate_status: str,
        needs_human_review: bool = False,
    ):
        self.research_quality_score = research_quality_score
        self.research_confidence_score = research_confidence_score
        self.coverage_score = coverage_score
        self.critical_claim_coverage_score = critical_claim_coverage_score
        self.source_quality_score = source_quality_score
        self.primary_source_coverage = primary_source_coverage
        self.corroboration_score = corroboration_score
        self.freshness_score = freshness_score
        self.contradiction_resolution_score = contradiction_resolution_score
        self.evidence_specificity_score = evidence_specificity_score
        self.total_penalties = total_penalties
        self.quality_gate_status = quality_gate_status
        self.needs_human_review = needs_human_review

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_quality_score": self.research_quality_score,
            "research_confidence_score": self.research_confidence_score,
            "coverage_score": self.coverage_score,
            "critical_claim_coverage_score": self.critical_claim_coverage_score,
            "source_quality_score": self.source_quality_score,
            "primary_source_coverage": self.primary_source_coverage,
            "corroboration_score": self.corroboration_score,
            "freshness_score": self.freshness_score,
            "contradiction_resolution_score": self.contradiction_resolution_score,
            "evidence_specificity_score": self.evidence_specificity_score,
            "total_penalties": self.total_penalties,
            "quality_gate_status": self.quality_gate_status,
            "needs_human_review": self.needs_human_review,
        }


class ResearchQualityScorer:
    """Calculates overall research quality, confidence, penalties, and gate status."""

    @classmethod
    def evaluate_quality(
        cls,
        coverage_score: float,
        critical_claim_coverage_score: float,
        source_quality_score: float,
        primary_source_coverage: float,
        corroboration_score: float,
        freshness_score: float,
        has_unresolved_critical_contradictions: bool = False,
        unresolved_contradictions_count: int = 0,
        missing_critical_sources: bool = False,
        stale_critical_evidence: bool = False,
        is_high_risk: bool = False,
    ) -> QualityEvaluationResult:
        # Implemented formula weights:
        # Coverage: 20
        # Critical Claim Coverage: 20
        # Source Quality: 15
        # Primary Source Coverage: 15
        # Corroboration: 10
        # Freshness: 10
        # Contradiction Resolution: 5
        # Evidence Specificity: 5
        # Total: 100

        contra_res_score = 0.0 if has_unresolved_critical_contradictions else 100.0
        evidence_specificity = 85.0

        positive_score = (
            (coverage_score * 0.20)
            + (critical_claim_coverage_score * 0.20)
            + (source_quality_score * 0.15)
            + (primary_source_coverage * 0.15)
            + (corroboration_score * 0.10)
            + (freshness_score * 0.10)
            + (contra_res_score * 0.05)
            + (evidence_specificity * 0.05)
        )

        # Penalties
        penalties = 0.0
        if has_unresolved_critical_contradictions:
            penalties += min(25.0, unresolved_contradictions_count * 15.0)
        if missing_critical_sources:
            penalties += 15.0
        if stale_critical_evidence:
            penalties += 10.0

        final_quality = max(0.0, min(100.0, positive_score - penalties))

        # Confidence formula
        confidence = (
            (coverage_score * 0.35)
            + (source_quality_score * 0.30)
            + (primary_source_coverage * 0.20)
            + (freshness_score * 0.15)
            - (penalties * 0.5)
        )
        final_confidence = max(10.0, min(99.0, confidence))

        # Quality Gate
        # 0–49: FAIL, 50–64: INSUFFICIENT, 65–74: MORE_RESEARCH, 75–84: PASS, 85–94: STRONG, 95–100: EXCEPTIONAL
        pass_threshold = 90.0 if is_high_risk else 75.0
        needs_human_review = False

        if final_quality >= 95.0:
            gate_status = "EXCEPTIONAL"
        elif final_quality >= 85.0:
            gate_status = "STRONG"
        elif final_quality >= pass_threshold:
            gate_status = "PASS"
        elif final_quality >= 65.0:
            gate_status = "MORE_RESEARCH"
        elif final_quality >= 50.0:
            gate_status = "INSUFFICIENT"
        else:
            gate_status = "FAIL"

        if is_high_risk and (final_quality < 90.0 or has_unresolved_critical_contradictions):
            needs_human_review = True

        return QualityEvaluationResult(
            research_quality_score=round(final_quality, 1),
            research_confidence_score=round(final_confidence, 1),
            coverage_score=round(coverage_score, 1),
            critical_claim_coverage_score=round(critical_claim_coverage_score, 1),
            source_quality_score=round(source_quality_score, 1),
            primary_source_coverage=round(primary_source_coverage, 1),
            corroboration_score=round(corroboration_score, 1),
            freshness_score=round(freshness_score, 1),
            contradiction_resolution_score=round(contra_res_score, 1),
            evidence_specificity_score=round(evidence_specificity, 1),
            total_penalties=round(penalties, 1),
            quality_gate_status=gate_status,
            needs_human_review=needs_human_review,
        )
