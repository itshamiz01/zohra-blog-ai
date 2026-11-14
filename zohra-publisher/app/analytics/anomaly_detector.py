"""
Zohra — Anomaly Detection Engine (Part 8).

Detects statistical anomalies in search performance metrics by comparing
recent observed values against rolling historical baselines.

Key principles:
- Volume significance gates: anomalies require minimum data thresholds
- Distinguishes site-wide vs. page-specific shifts
- Never fabricates baseline data (null ≠ 0)
- Severity classified by magnitude and confidence
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.schemas.analytics import AnomalyScope, AnomalySeverity

logger = get_logger("analytics.anomaly_detector")


def detect_metric_anomaly(
    metric_name: str,
    observed_value: float,
    baseline_values: list[float],
    site_id: uuid.UUID,
    article_id: uuid.UUID | None = None,
    min_baseline_points: int = 7,
    min_volume: int = 50,
    current_volume: int = 0,
    z_threshold: float = 2.0,
) -> dict[str, Any] | None:
    """Detect a statistical anomaly for a single metric.

    Args:
        metric_name: Name of the metric (clicks, impressions, ctr, avg_position).
        observed_value: Current period value.
        baseline_values: Historical baseline values (e.g., past 28 daily values).
        site_id: Site UUID.
        article_id: Optional article UUID (None for site-wide metrics).
        min_baseline_points: Minimum historical data points needed.
        min_volume: Minimum volume threshold for significance.
        current_volume: Current period volume for significance gating.
        z_threshold: Z-score threshold for anomaly detection.

    Returns:
        Anomaly dict or None if no anomaly detected.
    """
    # Significance gate
    if len(baseline_values) < min_baseline_points:
        return None

    if current_volume < min_volume and metric_name not in ("avg_position",):
        return None

    baseline_mean = sum(baseline_values) / len(baseline_values)
    if baseline_mean == 0:
        return None

    # Standard deviation
    variance = sum((v - baseline_mean) ** 2 for v in baseline_values) / len(baseline_values)
    std_dev = variance ** 0.5

    if std_dev == 0:
        # All baseline values identical — any change is an anomaly
        if observed_value == baseline_mean:
            return None
        std_dev = max(abs(baseline_mean) * 0.01, 0.001)  # synthetic small std

    z_score = (observed_value - baseline_mean) / std_dev

    if abs(z_score) < z_threshold:
        return None

    # Calculate changes
    absolute_change = round(observed_value - baseline_mean, 4)
    percentage_change = round(((observed_value - baseline_mean) / baseline_mean) * 100, 2)

    # Severity classification
    severity = _classify_severity(abs(z_score), abs(percentage_change))

    # Scope determination
    scope = AnomalyScope.PAGE_SPECIFIC.value if article_id else AnomalyScope.SITE_WIDE.value

    return {
        "site_id": site_id,
        "article_id": article_id,
        "metric": metric_name,
        "baseline_value": round(baseline_mean, 4),
        "observed_value": round(observed_value, 4),
        "absolute_change": absolute_change,
        "percentage_change": percentage_change,
        "severity": severity,
        "confidence": min(round(abs(z_score) / 4.0, 2), 1.0),
        "possible_scope": scope,
        "details_json": {
            "z_score": round(z_score, 3),
            "std_dev": round(std_dev, 4),
            "baseline_points": len(baseline_values),
            "current_volume": current_volume,
        },
        "detected_at": datetime.now(UTC),
    }


def _classify_severity(abs_z_score: float, abs_pct_change: float) -> str:
    """Classify anomaly severity from z-score and percentage change magnitude."""
    if abs_z_score >= 4.0 or abs_pct_change >= 80:
        return AnomalySeverity.CRITICAL.value
    if abs_z_score >= 3.0 or abs_pct_change >= 50:
        return AnomalySeverity.HIGH.value
    if abs_z_score >= 2.5 or abs_pct_change >= 30:
        return AnomalySeverity.MEDIUM.value
    if abs_z_score >= 2.0 or abs_pct_change >= 15:
        return AnomalySeverity.LOW.value
    return AnomalySeverity.INFO.value


def detect_site_vs_page_anomaly(
    page_anomalies: list[dict[str, Any]],
    site_anomaly: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Distinguish page-specific anomalies from site-wide shifts.

    If the site itself is experiencing the same directional change,
    individual page anomalies are downgraded to SITE_WIDE scope.
    """
    if not site_anomaly or not page_anomalies:
        return page_anomalies

    site_direction = 1 if site_anomaly["percentage_change"] > 0 else -1

    adjusted = []
    for anomaly in page_anomalies:
        page_direction = 1 if anomaly["percentage_change"] > 0 else -1
        if page_direction == site_direction:
            anomaly = {**anomaly, "possible_scope": AnomalyScope.SITE_WIDE.value}
        adjusted.append(anomaly)

    return adjusted
