"""
Zohra — Coverage Analyzer & Research Gap Engine.

Evaluates evidence completeness across questions, heavily weighting critical questions,
detects gaps (missing primary source, uncorroborated claims, contradictions), and enforces stop conditions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.schemas.research import GapType, QuestionPriority


class CoverageEvaluation:
    def __init__(
        self,
        coverage_score: float,
        critical_claim_coverage_score: float,
        answered_questions: list[dict[str, Any]],
        partially_answered_questions: list[dict[str, Any]],
        unanswered_questions: list[dict[str, Any]],
        gaps: list[dict[str, Any]],
        should_stop: bool,
        stop_reason: str,
        follow_up_queries: list[str],
    ):
        self.coverage_score = coverage_score
        self.critical_claim_coverage_score = critical_claim_coverage_score
        self.answered_questions = answered_questions
        self.partially_answered_questions = partially_answered_questions
        self.unanswered_questions = unanswered_questions
        self.gaps = gaps
        self.should_stop = should_stop
        self.stop_reason = stop_reason
        self.follow_up_queries = follow_up_queries

    def to_dict(self) -> dict[str, Any]:
        return {
            "coverage_score": self.coverage_score,
            "critical_claim_coverage_score": self.critical_claim_coverage_score,
            "answered_count": len(self.answered_questions),
            "unanswered_count": len(self.unanswered_questions),
            "gaps_count": len(self.gaps),
            "should_stop": self.should_stop,
            "stop_reason": self.stop_reason,
            "follow_up_queries": self.follow_up_queries,
        }


class CoverageAnalyzer:
    """Evaluates question coverage, priority-weighted scores, gaps, and stop conditions."""

    PRIORITY_WEIGHTS = {
        QuestionPriority.CRITICAL.value: 4.0,
        QuestionPriority.HIGH.value: 2.5,
        QuestionPriority.MEDIUM.value: 1.5,
        QuestionPriority.LOW.value: 1.0,
    }

    @classmethod
    def evaluate_coverage(
        cls,
        questions: Sequence[dict[str, Any]],
        claims: Sequence[dict[str, Any]],
        iteration: int = 1,
        max_iterations: int = 3,
        actual_cost: float = 0.0,
        budget_limit: float = 5.0,
        is_expired: bool = False,
    ) -> CoverageEvaluation:
        total_weight = 0.0
        earned_weight = 0.0

        critical_total = 0.0
        critical_earned = 0.0

        answered: list[dict[str, Any]] = []
        partial: list[dict[str, Any]] = []
        unanswered: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        follow_ups: list[str] = []

        for q in questions:
            q_id = str(q.get("id", ""))
            q_text = q.get("question", "")
            q_prio = q.get("priority", "MEDIUM")
            req_prim = bool(q.get("requires_primary_source", False))
            req_mult = bool(q.get("requires_multiple_sources", False))
            q_type = q.get("question_type", "product")

            weight = cls.PRIORITY_WEIGHTS.get(q_prio, 1.5)
            total_weight += weight
            is_critical = (q_prio == QuestionPriority.CRITICAL.value)
            if is_critical:
                critical_total += 1.0

            # Match claims that address this question
            stopwords = {"what", "is", "the", "a", "an", "and", "of", "in", "to", "for", "who", "was", "does", "how", "it", "its"}
            q_content_words = {w for w in q_text.lower().split() if w not in stopwords}
            matching_claims = []
            q_t_clean = q_type.lower()

            for c in claims:
                c_text = c.get("claim_text", "").lower()
                c_words = {w for w in c_text.split() if w not in stopwords}
                c_pred = (c.get("predicate") or "").lower()
                has_type_match = bool(
                    q_t_clean
                    and c_pred
                    and q_t_clean not in ("product", "definition", "statement")
                    and (q_t_clean in c_pred or c_pred in q_t_clean)
                )
                if len(q_content_words.intersection(c_words)) >= 2 or has_type_match:
                    matching_claims.append(c)


            has_primary = any(c.get("has_primary_source") for c in matching_claims)
            has_corroborated = any(c.get("verification_level", 0) >= 3 for c in matching_claims)

            if not matching_claims:
                unanswered.append({"question_id": q_id, "question": q_text, "priority": q_prio})
                gaps.append({
                    "question_id": q_id,
                    "gap_type": GapType.NO_SOURCE.value,
                    "description": f"No evidence found for: {q_text}",
                    "importance": q_prio.lower(),
                    "recommended_action": f"Search targeted query for {q_text}",
                })
                follow_ups.append(f"{q_text} official")
            elif req_prim and not has_primary:
                partial.append({"question_id": q_id, "question": q_text, "priority": q_prio})
                earned_weight += weight * 0.4
                if is_critical:
                    critical_earned += 0.4
                gaps.append({
                    "question_id": q_id,
                    "gap_type": GapType.MISSING_PRIMARY_SOURCE.value,
                    "description": f"Missing primary source documentation for: {q_text}",
                    "importance": q_prio.lower(),
                    "recommended_action": f"Search official site: {q_text}",
                })
                follow_ups.append(f"official documentation {q_text}")
            elif req_mult and not has_corroborated and len(matching_claims) < 2:
                partial.append({"question_id": q_id, "question": q_text, "priority": q_prio})
                earned_weight += weight * 0.6
                if is_critical:
                    critical_earned += 0.6
                gaps.append({
                    "question_id": q_id,
                    "gap_type": GapType.INSUFFICIENT_CORROBORATION.value,
                    "description": f"Needs independent corroboration: {q_text}",
                    "importance": q_prio.lower(),
                    "recommended_action": f"Search independent reviews: {q_text}",
                })
            else:
                answered.append({
                    "question_id": q_id,
                    "question": q_text,
                    "priority": q_prio,
                    "claim_count": len(matching_claims),
                })
                earned_weight += weight
                if is_critical:
                    critical_earned += 1.0

        # Compute priority-weighted coverage score
        coverage_score = round((earned_weight / total_weight) * 100.0, 1) if total_weight > 0 else 0.0
        crit_score = round((critical_earned / critical_total) * 100.0, 1) if critical_total > 0 else 100.0

        # Evaluate Stop Conditions
        should_stop = False
        stop_reason = "in_progress"

        if is_expired:
            should_stop = True
            stop_reason = "opportunity_expired"
        elif actual_cost >= budget_limit:
            should_stop = True
            stop_reason = "budget_exhausted"
        elif coverage_score >= 85.0 and crit_score >= 85.0:
            should_stop = True
            stop_reason = "coverage_threshold_reached"
        elif iteration >= max_iterations:
            should_stop = True
            stop_reason = "max_iterations_reached"

        return CoverageEvaluation(
            coverage_score=coverage_score,
            critical_claim_coverage_score=crit_score,
            answered_questions=answered,
            partially_answered_questions=partial,
            unanswered_questions=unanswered,
            gaps=gaps,
            should_stop=should_stop,
            stop_reason=stop_reason,
            follow_up_queries=follow_ups[:3],
        )
