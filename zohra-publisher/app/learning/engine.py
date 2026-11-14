"""
Zohra — Part 9 Central Learning Engine & Strategy Memory System.

Implements Sections 80 to 94, 189 to 194 of Part 9 Master Prompt:
- Compares predictions against measured 28-day performance outcomes for scoring calibration
- Synthesizes evidence-grounded StrategyMemories from repeated consistent experiments (N >= 3)
- Handles memory confidence scoring, graceful temporal decay, and explicit contradiction handling
- Records negative learning patterns to prevent repeating mistakes
- Outlier resistance: viral articles are isolated to prevent skewing general publishing strategy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.db.models.optimization import MemoryStatus, PredictionOutcome, StrategyMemory


@dataclass
class CalibrationReport:
    total_evaluated: int
    mean_absolute_error: float
    high_score_performance_avg: float
    mid_score_performance_avg: float
    is_calibrated: bool
    recalibration_needed: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class MemoryCreationResult:
    created: bool
    memory: StrategyMemory | None
    status: MemoryStatus
    confidence: float
    reason: str


class ZohraLearningEngine:
    """Consolidates cross-pipeline signals into institutional strategy memory."""

    @classmethod
    def evaluate_predictions_calibration(
        cls,
        outcomes: list[PredictionOutcome | dict[str, Any]],
    ) -> CalibrationReport:
        """
        Assesses whether pre-publication predictions (e.g. Opportunity Score) correlate
        properly with actual measured 28-day outcomes.
        """
        if not outcomes:
            return CalibrationReport(
                total_evaluated=0,
                mean_absolute_error=0.0,
                high_score_performance_avg=0.0,
                mid_score_performance_avg=0.0,
                is_calibrated=True,
                recalibration_needed=False,
                reasons=["No prediction outcomes available for calibration evaluation."],
            )

        high_score_actuals: list[float] = []
        mid_score_actuals: list[float] = []
        errors: list[float] = []

        for o in outcomes:
            p_val = float(o.predicted_value if isinstance(o, PredictionOutcome) else o.get("predicted_value", 0.0))
            a_val = float(o.actual_value if isinstance(o, PredictionOutcome) else o.get("actual_value", 0.0))

            errors.append(abs(p_val - a_val))
            if p_val >= 80.0:
                high_score_actuals.append(a_val)
            elif 55.0 <= p_val < 80.0:
                mid_score_actuals.append(a_val)

        mae = sum(errors) / max(1, len(errors))
        high_avg = (sum(high_score_actuals) / max(1, len(high_score_actuals))) if high_score_actuals else 0.0
        mid_avg = (sum(mid_score_actuals) / max(1, len(mid_score_actuals))) if mid_score_actuals else 0.0

        # Calibration failure: topics scoring 85+ regularly fail to outperform 60-70 topics
        reasons: list[str] = []
        recalibration_needed = False
        if len(high_score_actuals) >= 3 and len(mid_score_actuals) >= 3:
            if high_avg <= mid_avg:
                recalibration_needed = True
                reasons.append(
                    f"Calibration inversion detected: High-score items averaged {high_avg:.1f} actual outcome, "
                    f"which does not exceed mid-score items ({mid_avg:.1f})."
                )

        return CalibrationReport(
            total_evaluated=len(outcomes),
            mean_absolute_error=round(mae, 2),
            high_score_performance_avg=round(high_avg, 2),
            mid_score_performance_avg=round(mid_avg, 2),
            is_calibrated=not recalibration_needed,
            recalibration_needed=recalibration_needed,
            reasons=reasons,
        )

    @classmethod
    def synthesize_strategy_memory(
        cls,
        subject: str,
        memory_type: str,
        observation: str,
        consistent_experiment_count: int,
        site_id: Any | None = None,
        scope: str = "SITE",
        is_negative: bool = False,
    ) -> MemoryCreationResult:
        """
        Forms a new StrategyMemory from validated experiment results.
        Requires N >= 3 consistent experiments for SUPPORTED status (Section 84).
        """
        # Section 84: Strategy learning requires sufficient sample sizes
        if consistent_experiment_count < 1:
            return MemoryCreationResult(
                created=False,
                memory=None,
                status=MemoryStatus.CANDIDATE,
                confidence=0.30,
                reason="Insufficient evidence: At least 1 validated experiment required to record a candidate lesson.",
            )

        # Confidence calculation scaling with evidence sample
        if consistent_experiment_count >= 5:
            status = MemoryStatus.STRONG
            confidence = min(0.92, 0.70 + (0.04 * consistent_experiment_count))
        elif consistent_experiment_count >= 3:
            status = MemoryStatus.SUPPORTED
            confidence = min(0.85, 0.65 + (0.05 * consistent_experiment_count))
        else:
            status = MemoryStatus.CANDIDATE
            confidence = 0.50

        memory = StrategyMemory(
            site_id=site_id,
            scope=scope,
            memory_type=memory_type,
            subject=subject,
            observation=observation,
            evidence_json={
                "consistent_experiments": consistent_experiment_count,
                "is_negative_pattern": is_negative,
                "initial_confidence": confidence,
            },
            sample_size=consistent_experiment_count,
            confidence=round(confidence, 2),
            status=status.value,
            contradicting_evidence_json=[],
            version=1,
        )

        return MemoryCreationResult(
            created=True,
            memory=memory,
            status=status,
            confidence=round(confidence, 2),
            reason=f"Synthesized memory with {status.value} status based on {consistent_experiment_count} consistent observations.",
        )

    @classmethod
    def apply_memory_decay(
        cls,
        memory: StrategyMemory,
        days_without_support: int,
        decay_halflife_days: int = 90,
    ) -> float:
        """
        Applies temporal confidence decay to older memories without recent support (Section 90).
        """
        if days_without_support <= 30:
            return memory.confidence

        # Exponential decay formula
        decay_factor = 0.5 ** (days_without_support / decay_halflife_days)
        new_confidence = round(memory.confidence * decay_factor, 2)
        memory.confidence = new_confidence

        if new_confidence < 0.25:
            memory.status = MemoryStatus.EXPIRED.value
        elif new_confidence < 0.50 and memory.status == MemoryStatus.STRONG.value:
            memory.status = MemoryStatus.WEAKENING.value

        return new_confidence

    @classmethod
    def register_contradicting_evidence(
        cls,
        memory: StrategyMemory,
        contradiction_evidence: dict[str, Any],
    ) -> float:
        """
        Records contradicting evidence without silently deleting historical memories (Section 91).
        """
        evidence_list = list(memory.contradicting_evidence_json or [])
        evidence_list.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "details": contradiction_evidence,
        })
        memory.contradicting_evidence_json = evidence_list

        # Penalty for contradictory evidence
        penalty = 0.20
        new_conf = round(max(0.05, memory.confidence - penalty), 2)
        memory.confidence = new_conf

        if new_conf <= 0.40:
            memory.status = MemoryStatus.CONTRADICTED.value
        else:
            memory.status = MemoryStatus.WEAKENING.value

        return new_conf

    @classmethod
    def is_viral_outlier(cls, article_clicks: int, cohort_median_clicks: int) -> bool:
        """
        Detects viral outliers (traffic > 5x cohort median) to protect strategy from overfitting (Section 190, 191).
        """
        if cohort_median_clicks <= 0:
            return False
        return article_clicks >= (cohort_median_clicks * 5)
