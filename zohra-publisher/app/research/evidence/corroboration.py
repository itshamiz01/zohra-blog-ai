"""
Zohra — Cross-Source Corroboration Engine.

Calculates verification level (0-5) across independent source groups, determines
claim status, confidence score, and enforces writer policies (safe_to_state vs do_not_state_as_fact).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.schemas.research import ClaimStatus, SupportDirection, WriterPolicy


class CorroborationResult:
    def __init__(
        self,
        verification_level: int,
        status: ClaimStatus,
        confidence_score: float,
        writer_policy: WriterPolicy,
        independent_sources_count: int,
        has_primary_source: bool,
        has_contradictions: bool,
    ):
        self.verification_level = verification_level
        self.status = status
        self.confidence_score = confidence_score
        self.writer_policy = writer_policy
        self.independent_sources_count = independent_sources_count
        self.has_primary_source = has_primary_source
        self.has_contradictions = has_contradictions

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_level": self.verification_level,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "writer_policy": self.writer_policy.value,
            "independent_sources_count": self.independent_sources_count,
            "has_primary_source": self.has_primary_source,
            "has_contradictions": self.has_contradictions,
        }


class CorroborationEngine:
    """Evaluates cross-source corroboration using independence groups and primary-source validation."""

    @classmethod
    def evaluate_claim_corroboration(
        cls,
        evidence_items: Sequence[dict[str, Any]],
        attribution_required: bool = False,
        time_sensitive: bool = False,
    ) -> CorroborationResult:
        if not evidence_items:
            return CorroborationResult(
                verification_level=0,
                status=ClaimStatus.UNVERIFIED,
                confidence_score=0.0,
                writer_policy=WriterPolicy.DO_NOT_STATE_AS_FACT,
                independent_sources_count=0,
                has_primary_source=False,
                has_contradictions=False,
            )

        supporting_groups: set[str] = set()
        has_primary = False
        contradicting_items = 0
        total_strength = 0.0

        for item in evidence_items:
            direction = item.get("support_direction", SupportDirection.CONTEXT_ONLY.value)
            group_id = item.get("independence_group_id") or str(item.get("source_id", ""))
            is_prim = bool(item.get("is_primary_source", False))
            strength = float(item.get("evidence_strength_score", 0.5))

            if direction == SupportDirection.SUPPORTS.value:
                supporting_groups.add(group_id)
                total_strength += strength
                if is_prim:
                    has_primary = True
            elif direction == SupportDirection.CONTRADICTS.value:
                contradicting_items += 1

        indep_count = len(supporting_groups)
        has_contradictions = contradicting_items > 0

        # Handle explicit contradictions
        if has_contradictions and indep_count <= contradicting_items:
            return CorroborationResult(
                verification_level=1,
                status=ClaimStatus.DISPUTED,
                confidence_score=35.0,
                writer_policy=WriterPolicy.DO_NOT_STATE_AS_FACT,
                independent_sources_count=indep_count,
                has_primary_source=has_primary,
                has_contradictions=True,
            )

        # Calculate Verification Level (0 to 5)
        # Level 5: Primary + >= 2 independent secondary sources
        if has_primary and indep_count >= 3:
            v_level = 5
            status = ClaimStatus.STRONGLY_SUPPORTED
            confidence = min(98.0, 85.0 + (indep_count * 3.0))
        # Level 4: Primary + >= 1 independent secondary source
        elif has_primary and indep_count >= 2:
            v_level = 4
            status = ClaimStatus.STRONGLY_SUPPORTED
            confidence = 90.0
        # Level 3: Multiple independent secondary sources (no primary)
        elif indep_count >= 2:
            v_level = 3
            status = ClaimStatus.SUPPORTED
            confidence = 80.0
        # Level 2: Single strong primary source or high quality source
        elif has_primary or (indep_count == 1 and total_strength >= 0.75):
            v_level = 2
            status = ClaimStatus.SUPPORTED
            confidence = 72.0
        # Level 1: Single low/moderate quality source
        elif indep_count == 1:
            v_level = 1
            status = ClaimStatus.WEAKLY_SUPPORTED
            confidence = 45.0
        else:
            v_level = 0
            status = ClaimStatus.UNVERIFIED
            confidence = 10.0

        # Determine Writer Policy
        if status in (ClaimStatus.STRONGLY_SUPPORTED, ClaimStatus.SUPPORTED):
            if attribution_required:
                writer_policy = WriterPolicy.REQUIRE_ATTRIBUTION
            elif time_sensitive:
                writer_policy = WriterPolicy.TIME_SENSITIVE_CONTEXT
            else:
                writer_policy = WriterPolicy.SAFE_TO_STATE
        elif status == ClaimStatus.WEAKLY_SUPPORTED:
            writer_policy = WriterPolicy.REQUIRE_ATTRIBUTION if attribution_required else WriterPolicy.DO_NOT_STATE_AS_FACT
        else:
            writer_policy = WriterPolicy.DO_NOT_STATE_AS_FACT

        return CorroborationResult(
            verification_level=v_level,
            status=status,
            confidence_score=round(confidence, 1),
            writer_policy=writer_policy,
            independent_sources_count=indep_count,
            has_primary_source=has_primary,
            has_contradictions=has_contradictions,
        )
