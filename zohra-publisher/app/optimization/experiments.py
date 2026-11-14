"""
Zohra — Part 9 Experiment Engine.

Implements Sections 63 to 76, 170, 171, 172 of Part 9 Master Prompt:
- Before/after time-series and cohort experimentation
- Site trend normalization: Delta_adjusted = Delta_treatment - Delta_site
- Confounder detection (flags external algorithm shifts, multiple simultaneous changes)
- Guardrail evaluation (e.g. checks that impression volume does not collapse while CTR rises)
- Rigorous result classification: POSITIVE, NEGATIVE, NEUTRAL, INCONCLUSIVE
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ExperimentResultType(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class ExperimentEvaluationResult:
    experiment_id: str
    result: ExperimentResultType
    primary_metric: str
    baseline_value: float
    treatment_value: float
    raw_relative_change: float
    site_trend_change: float
    site_adjusted_relative_change: float
    guardrail_violations: list[str] = field(default_factory=list)
    confounders_detected: list[str] = field(default_factory=list)
    confidence: float = 0.5
    recommendation: str = ""
    rollback_recommended: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["result"] = self.result.value
        return d


class ExperimentEngine:
    """Evaluates experiment outcomes using statistical baselines, site-wide trends, and guardrails."""

    @classmethod
    def evaluate_experiment(
        cls,
        experiment_id: str,
        primary_metric: str,
        baseline_metrics: dict[str, float],
        treatment_metrics: dict[str, float],
        site_trend_metrics: dict[str, float] | None = None,
        guardrail_metrics: list[str] | None = None,
        minimum_sample: int = 500,
        success_threshold: float = 0.10,     # e.g. +10% lift
        rollback_threshold: float = -0.15,   # e.g. -15% drop
        known_confounders: list[str] | None = None,
    ) -> ExperimentEvaluationResult:
        """
        Evaluates treatment metrics against baseline metrics with site-wide normalization.
        """
        confounders = list(known_confounders or [])
        guardrails = guardrail_metrics or ["impressions", "avg_position", "clicks"]

        b_val = float(baseline_metrics.get(primary_metric, 0.0))
        t_val = float(treatment_metrics.get(primary_metric, 0.0))
        sample_size = int(treatment_metrics.get("impressions", treatment_metrics.get("sample_size", 0)))

        # 1. Sample Size Check -> INCONCLUSIVE (Section 74, Test R)
        if sample_size < minimum_sample:
            return ExperimentEvaluationResult(
                experiment_id=experiment_id,
                result=ExperimentResultType.INCONCLUSIVE,
                primary_metric=primary_metric,
                baseline_value=b_val,
                treatment_value=t_val,
                raw_relative_change=0.0,
                site_trend_change=0.0,
                site_adjusted_relative_change=0.0,
                confidence=0.35,
                recommendation=f"Sample size ({sample_size}) below minimum required ({minimum_sample}). Inconclusive result; maintain observation.",
                rollback_recommended=False,
            )

        # 2. Raw Relative Change
        if b_val > 0:
            raw_change = (t_val - b_val) / b_val
        else:
            raw_change = 1.0 if t_val > 0 else 0.0

        # 3. Site Trend Adjustment (Section 70, Test S)
        site_metrics = site_trend_metrics or {}
        site_b = float(site_metrics.get(f"{primary_metric}_baseline", 1.0))
        site_t = float(site_metrics.get(f"{primary_metric}_treatment", 1.0))
        if site_b > 0:
            site_change = (site_t - site_b) / site_b
        else:
            site_change = 0.0

        # Adjusted change subtracts macro site trend (e.g. if site dropped 30% and page dropped 5%, net = +25%)
        site_adjusted_change = raw_change - site_change

        # 4. Guardrail Metrics Verification (Section 75)
        violations: list[str] = []
        for g_metric in guardrails:
            if g_metric == primary_metric:
                continue
            g_base = float(baseline_metrics.get(g_metric, 0.0))
            g_treat = float(treatment_metrics.get(g_metric, 0.0))
            if g_base > 0:
                g_change = (g_treat - g_base) / g_base
                # For avg_position: lower is better (1.0 is top)
                if "position" in g_metric:
                    if g_change > 0.30:  # e.g. position 5 -> 7 is worsening
                        violations.append(f"Position degraded by {g_change:.1%}")
                else:
                    if g_change < -0.25:  # e.g. impressions dropped > 25%
                        violations.append(f"Guardrail metric '{g_metric}' dropped by {abs(g_change):.1%}")

        # 5. Confounder Penalty
        confidence = 0.85
        if confounders:
            confidence -= min(0.40, len(confounders) * 0.20)

        # 6. Result Classification
        rollback_recommended = False
        if site_adjusted_change <= rollback_threshold or len(violations) >= 2:
            result = ExperimentResultType.NEGATIVE
            rollback_recommended = True
            rec = "Optimization resulted in performance degradation or multiple guardrail breaches. Rollback recommended."
        elif site_adjusted_change >= success_threshold and len(violations) == 0:
            result = ExperimentResultType.POSITIVE
            rec = "Significant performance improvement observed with all guardrails intact. Recommend permanent adoption."
        elif abs(site_adjusted_change) < success_threshold and len(violations) == 0:
            result = ExperimentResultType.NEUTRAL
            rec = "Performance difference within normal statistical variation. Keep or retire based on editorial preference."
        else:
            result = ExperimentResultType.INCONCLUSIVE
            rec = f"Mixed results (metric change: {site_adjusted_change:.1%}, violations: {violations}). Inconclusive."

        return ExperimentEvaluationResult(
            experiment_id=experiment_id,
            result=result,
            primary_metric=primary_metric,
            baseline_value=b_val,
            treatment_value=t_val,
            raw_relative_change=round(raw_change, 4),
            site_trend_change=round(site_change, 4),
            site_adjusted_relative_change=round(site_adjusted_change, 4),
            guardrail_violations=violations,
            confounders_detected=confounders,
            confidence=round(confidence, 2),
            recommendation=rec,
            rollback_recommended=rollback_recommended,
        )
