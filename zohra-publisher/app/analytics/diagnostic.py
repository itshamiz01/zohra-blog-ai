"""
Zohra — Performance Diagnostics Engine (Part 8).

Provides structured diagnostics that clearly separate:
- OBSERVED FACTS: verified data from Search Console
- HYPOTHESES: plausible explanations inferred from patterns
- DATA QUALITY CAVEATS: known limitations of the data

This separation is the cornerstone of Part 8's integrity:
Part 8 must NEVER present a hypothesis as an observation.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.logging import get_logger
from app.schemas.analytics import PerformanceDiagnostic

logger = get_logger("analytics.diagnostic")


def build_diagnostic(
    article_id: uuid.UUID,
    metrics: dict[str, Any],
    indexing_status: str | None = None,
    anomalies: list[dict[str, Any]] | None = None,
    cannibalization: list[dict[str, Any]] | None = None,
    ctr_diagnostic: dict[str, Any] | None = None,
    ranking_trend: dict[str, Any] | None = None,
) -> PerformanceDiagnostic:
    """Build a structured diagnostic for an article's search performance.

    Every fact is grounded in observed GSC data. Every hypothesis
    is explicitly labeled as such.
    """
    observed = []
    hypotheses = []
    caveats = []

    # ── Observed Facts ────────────────────────────────────────────

    clicks = metrics.get("clicks", 0)
    impressions = metrics.get("impressions", 0)
    avg_position = metrics.get("avg_position")
    ctr = metrics.get("ctr")

    if impressions > 0:
        observed.append(
            f"Article received {impressions:,} impressions and {clicks:,} clicks."
        )
    else:
        observed.append("Article has received zero impressions in the measurement window.")

    if avg_position is not None:
        observed.append(f"Average ranking position: {avg_position:.1f}.")

    if ctr is not None:
        observed.append(f"Click-through rate: {ctr:.2%}.")

    # Indexing status observation
    if indexing_status:
        observed.append(f"Indexing status: {indexing_status}.")

    # Anomaly observations
    if anomalies:
        for a in anomalies:
            metric_name = a.get("metric", "unknown")
            pct = a.get("percentage_change", 0)
            direction = "increased" if pct > 0 else "decreased"
            observed.append(
                f"Anomaly detected: {metric_name} {direction} by {abs(pct):.1f}% "
                f"vs. baseline (severity: {a.get('severity', 'UNKNOWN')})."
            )

    # Cannibalization observation
    if cannibalization:
        for c in cannibalization:
            observed.append(
                f"Cannibalization detected: {len(c.get('article_ids', []))} articles "
                f"competing for query '{c.get('query', '?')}' with "
                f"{c.get('ownership_switch_count', 0)} ownership switches."
            )

    # CTR diagnostic observation
    if ctr_diagnostic:
        if ctr_diagnostic.get("underperforming"):
            observed.append(
                f"CTR ({ctr_diagnostic.get('actual_ctr', 0):.2%}) is below site "
                f"benchmark average ({ctr_diagnostic.get('benchmark_avg_ctr', 0):.2%}) "
                f"for position band {ctr_diagnostic.get('position_band', '?')}."
            )

    # Ranking trend observation
    if ranking_trend:
        delta = ranking_trend.get("position_delta")
        trend = ranking_trend.get("trend", "INSUFFICIENT_DATA")
        if delta is not None:
            direction = "improved" if delta < 0 else "worsened"
            observed.append(
                f"Ranking trend: position {direction} by {abs(delta):.1f} "
                f"(trend: {trend})."
            )

    # ── Hypotheses (clearly labeled) ──────────────────────────────

    if indexing_status and indexing_status not in ("INDEXED",):
        hypotheses.append(
            f"HYPOTHESIS: The article may not be receiving organic traffic because "
            f"its indexing status is '{indexing_status}'. This could be due to "
            f"technical issues (robots.txt, canonical mismatch) or content quality signals."
        )

    if avg_position is not None and avg_position > 10:
        hypotheses.append(
            "HYPOTHESIS: The article ranks beyond page 1 (position > 10). "
            "Content optimization or additional internal linking may improve visibility."
        )

    if ctr_diagnostic and ctr_diagnostic.get("underperforming"):
        hypotheses.append(
            "HYPOTHESIS: Low CTR relative to position suggests the title/meta description "
            "may not be compelling enough. This is a hypothesis — CTR can vary by "
            "query intent and SERP features."
        )

    if cannibalization:
        hypotheses.append(
            "HYPOTHESIS: Query cannibalization may be splitting click potential "
            "across multiple pages. Consolidating content or clarifying topic "
            "differentiation may help."
        )

    if not observed:
        caveats.append(
            "Insufficient data to generate meaningful observations. "
            "The article may be too new or have no Search Console data yet."
        )

    # ── Data Quality Caveats ──────────────────────────────────────

    if impressions < 100:
        caveats.append(
            "LOW SAMPLE SIZE: Fewer than 100 impressions. Metrics may not be "
            "statistically reliable."
        )

    caveats.append(
        "Search Console data has a 2-3 day reporting lag. Very recent changes "
        "may not yet be reflected."
    )

    caveats.append(
        "Position data represents weighted averages and may mask ranking "
        "variability across different queries, devices, and locations."
    )

    # ── Confidence Level ──────────────────────────────────────────

    confidence = "LOW"
    if impressions >= 500 and len(observed) >= 3:
        confidence = "HIGH"
    elif impressions >= 100 and len(observed) >= 2:
        confidence = "MEDIUM"

    # ── Summary ───────────────────────────────────────────────────

    summary_parts = []
    if impressions == 0:
        summary_parts.append("No search visibility in the measurement window.")
    elif avg_position is not None and avg_position <= 10:
        summary_parts.append(f"Article ranks on page 1 (avg pos {avg_position:.1f}).")
    elif avg_position is not None:
        summary_parts.append(f"Article ranks on page {int(avg_position // 10) + 1} (avg pos {avg_position:.1f}).")

    if hypotheses:
        summary_parts.append(f"{len(hypotheses)} hypothesis(es) generated.")

    return PerformanceDiagnostic(
        article_id=article_id,
        observed_facts=observed,
        hypotheses=hypotheses,
        data_quality_caveats=caveats,
        confidence_level=confidence,
        summary=" ".join(summary_parts) if summary_parts else "No diagnostic data available.",
    )
