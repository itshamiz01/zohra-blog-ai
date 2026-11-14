"""
Zohra — Independent Grounding Scorer (Part 6).

Calculates independent part6_grounding_score without trusting Part 5's claims.
Weights material claims by importance (critical = 5, major = 3, supporting = 1)
and applies steep penalties for contradicted, fabricated, or scope-expanded claims.
"""

from __future__ import annotations

from app.schemas.audit import ClaimMatchResult, ClaimVerificationStatus


class GroundingScorer:
    """Calculates independent grounding scores from verification results."""

    IMPORTANCE_WEIGHTS = {
        "critical": 5.0,
        "major": 3.0,
        "supporting": 1.0,
    }

    STATUS_CREDIT = {
        ClaimVerificationStatus.SUPPORTED: 1.0,
        ClaimVerificationStatus.PARTIALLY_SUPPORTED: 0.6,
        ClaimVerificationStatus.ATTRIBUTION_MISSING: 0.4,
        ClaimVerificationStatus.SCOPE_MISMATCH: 0.2,
        ClaimVerificationStatus.MISLEADING: 0.0,
        ClaimVerificationStatus.UNSUPPORTED: 0.0,
        ClaimVerificationStatus.OUTDATED: 0.0,
        ClaimVerificationStatus.CONTRADICTED: -0.5,
    }

    def calculate_score(self, claim_results: list[ClaimMatchResult]) -> float:
        """Returns grounding score between 0.0 and 100.0."""
        if not claim_results:
            return 100.0

        total_weight = 0.0
        earned_weight = 0.0

        for res in claim_results:
            w = self.IMPORTANCE_WEIGHTS.get(res.importance.lower(), 1.0)
            credit = self.STATUS_CREDIT.get(res.verification_status, 0.0)

            total_weight += w
            earned_weight += w * credit

        if total_weight <= 0.0:
            return 100.0

        raw_score = (earned_weight / total_weight) * 100.0
        return max(0.0, min(100.0, round(raw_score, 2)))
