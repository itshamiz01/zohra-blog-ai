"""
Zohra — Part 9 Strategy Parameter Controller, Shadow Mode & Version Manager.

Implements Sections 95 to 99, 178 to 185 of Part 9 Master Prompt:
- Bounded parameter adjustments: strictly limits step rate (<= 25%) and enforces min/max clamping
- Strategy versioning across lifecycle: PROPOSED -> SHADOW -> VALIDATING -> ACTIVE -> ROLLBACK
- Shadow mode evaluation: records counterfactual decisions without altering live production decisions
- Atomic version promotion and instant fallback rollback capability
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.db.models.optimization import (
    StrategyParameter,
    StrategyVersion,
    StrategyVersionStatus,
)


@dataclass
class ParameterAdjustmentResult:
    parameter_name: str
    previous_value: float
    requested_value: float
    applied_value: float
    clamped: bool
    rate_limited: bool
    reason: str


@dataclass
class ShadowEvaluationDecision:
    item_id: str
    active_decision: Any
    shadow_decision: Any
    would_change: bool
    explanation: str


class StrategyParameterController:
    """Manages bounded, evidence-grounded adjustments to site strategy configuration."""

    MAX_STEP_PERCENT = 0.25  # Max 25% adjustment per step (Section 98)

    @classmethod
    def apply_bounded_adjustment(
        cls,
        param: StrategyParameter,
        proposed_value: float,
        evidence_ref: str | None = None,
        confidence: float = 0.75,
    ) -> ParameterAdjustmentResult:
        """
        Safely applies a bounded change to a StrategyParameter with step-rate limiting and boundary clamping.
        """
        prev = param.current_value
        requested = float(proposed_value)
        rate_limited = False
        clamped = False

        # 1. Step Rate Limit Check (Section 98)
        # Prevents violent swings (e.g. 0.20 -> 0.90 in one step)
        if prev > 0:
            max_delta = prev * cls.MAX_STEP_PERCENT
            delta = requested - prev
            if abs(delta) > max_delta:
                rate_limited = True
                clamped_target = prev + (max_delta if delta > 0 else -max_delta)
            else:
                clamped_target = requested
        else:
            clamped_target = requested

        # 2. Hard Minimum / Maximum Boundary Clamping (Section 95)
        if clamped_target > param.maximum_value:
            clamped = True
            final_val = param.maximum_value
        elif clamped_target < param.minimum_value:
            clamped = True
            final_val = param.minimum_value
        else:
            final_val = clamped_target

        final_val = round(final_val, 4)

        # Update Parameter Record
        param.rollback_value = prev
        param.previous_value = prev
        param.current_value = final_val
        param.confidence = confidence
        param.evidence_reference = evidence_ref
        param.last_changed_at = datetime.now(UTC)

        reason = (
            f"Adjusted from {prev} to {final_val}."
            + (" (Rate-limited to 25% max step)" if rate_limited else "")
            + (" (Clamped to parameter bounds)" if clamped else "")
        )

        return ParameterAdjustmentResult(
            parameter_name=param.parameter_name,
            previous_value=prev,
            requested_value=requested,
            applied_value=final_val,
            clamped=clamped,
            rate_limited=rate_limited,
            reason=reason,
        )


class StrategyVersionManager:
    """Orchestrates strategy version lifecycles, shadow evaluation, and promotion."""

    @classmethod
    def create_shadow_version(
        cls,
        site_id: Any,
        version_label: str,
        parameters: dict[str, float],
        reason: str,
    ) -> StrategyVersion:
        """
        Creates a new StrategyVersion in SHADOW mode for safe counterfactual evaluation.
        """
        return StrategyVersion(
            site_id=site_id,
            version=version_label,
            parameters_json=parameters,
            status=StrategyVersionStatus.SHADOW.value,
            reason=reason,
            evidence_json={"created_at": datetime.now(UTC).isoformat()},
        )

    @classmethod
    def evaluate_shadow_decision(
        cls,
        item_id: str,
        active_weights: dict[str, float],
        shadow_weights: dict[str, float],
        scoring_func: Any,
        item_data: dict[str, Any],
    ) -> ShadowEvaluationDecision:
        """
        Calculates what the system would have chosen under the shadow strategy
        versus what was actually chosen under the active strategy.
        """
        active_score = scoring_func(item_data, active_weights)
        shadow_score = scoring_func(item_data, shadow_weights)

        would_change = abs(active_score - shadow_score) > 5.0
        return ShadowEvaluationDecision(
            item_id=item_id,
            active_decision=active_score,
            shadow_decision=shadow_score,
            would_change=would_change,
            explanation=f"Active score: {active_score:.1f}, Shadow score: {shadow_score:.1f}.",
        )

    @classmethod
    def promote_to_active(
        cls,
        new_version: StrategyVersion,
        currently_active_version: StrategyVersion | None = None,
    ) -> tuple[StrategyVersion, StrategyVersion | None]:
        """
        Promotes a validated shadow version to ACTIVE and archives/retires the old version.
        """
        if currently_active_version:
            currently_active_version.status = StrategyVersionStatus.RETIRED.value
            currently_active_version.retired_at = datetime.now(UTC)

        new_version.status = StrategyVersionStatus.ACTIVE.value
        new_version.activated_at = datetime.now(UTC)

        return new_version, currently_active_version

    @classmethod
    def rollback_version(
        cls,
        failing_active_version: StrategyVersion,
        previous_version: StrategyVersion,
    ) -> tuple[StrategyVersion, StrategyVersion]:
        """
        Rolls back the active version to the previous known good version.
        """
        failing_active_version.status = StrategyVersionStatus.ROLLBACK.value
        failing_active_version.retired_at = datetime.now(UTC)

        previous_version.status = StrategyVersionStatus.ACTIVE.value
        previous_version.activated_at = datetime.now(UTC)

        return previous_version, failing_active_version
