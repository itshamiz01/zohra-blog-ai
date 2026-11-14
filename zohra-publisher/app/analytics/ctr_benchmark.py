"""
Zohra — CTR Benchmark Calculator (Part 8).

Computes empirical site-specific CTR distributions by position band,
device, and content type from normalized page_query_daily_metrics data.

Benchmarks are internal to the site — no external industry data is used.
This prevents hallucinated benchmarks by grounding all comparisons in
actual site performance.
"""

from __future__ import annotations

import statistics
import uuid

from app.core.logging import get_logger
from app.schemas.analytics import CTRDiagnosticResult, PositionBand

logger = get_logger("analytics.ctr_benchmark")


def position_to_band(position: float | None) -> PositionBand:
    """Map a numeric position to a human-readable position band."""
    if position is None:
        return PositionBand.NOT_RANKING
    if position <= 1.0:
        return PositionBand.TOP_1
    if position <= 3.0:
        return PositionBand.TOP_3
    if position <= 5.0:
        return PositionBand.TOP_5
    if position <= 10.0:
        return PositionBand.TOP_10
    if position <= 20.0:
        return PositionBand.PAGE_2
    return PositionBand.PAGE_3_PLUS


def calculate_ctr_benchmark(
    ctr_values: list[float],
) -> dict[str, float]:
    """Calculate benchmark statistics from a list of CTR values.

    Returns dict with avg_ctr, median_ctr, p25_ctr, p75_ctr.
    """
    if not ctr_values:
        return {
            "avg_ctr": 0.0,
            "median_ctr": 0.0,
            "p25_ctr": 0.0,
            "p75_ctr": 0.0,
            "sample_size": 0,
        }

    sorted_values = sorted(ctr_values)
    n = len(sorted_values)

    avg_ctr = sum(sorted_values) / n
    median_ctr = statistics.median(sorted_values)

    # Percentiles
    p25_idx = max(0, int(n * 0.25) - 1)
    p75_idx = min(n - 1, int(n * 0.75))
    p25_ctr = sorted_values[p25_idx]
    p75_ctr = sorted_values[p75_idx]

    return {
        "avg_ctr": round(avg_ctr, 6),
        "median_ctr": round(median_ctr, 6),
        "p25_ctr": round(p25_ctr, 6),
        "p75_ctr": round(p75_ctr, 6),
        "sample_size": n,
    }


def diagnose_ctr(
    url: str,
    actual_ctr: float | None,
    avg_position: float | None,
    impressions: int,
    benchmark_avg_ctr: float,
    benchmark_median_ctr: float,
    article_id: uuid.UUID | None = None,
    min_impressions: int = 50,
) -> CTRDiagnosticResult:
    """Diagnose CTR performance relative to the internal site benchmark.

    A page is considered underperforming if its CTR is below the 25th
    percentile of the site's empirical CTR for the same position band
    AND has sufficient impressions.
    """
    band = position_to_band(avg_position)

    # CTR ratio: actual / benchmark average
    ctr_ratio = None
    if actual_ctr is not None and benchmark_avg_ctr > 0:
        ctr_ratio = round(actual_ctr / benchmark_avg_ctr, 4)

    sample_sufficient = impressions >= min_impressions
    underperforming = False

    if actual_ctr is not None and sample_sufficient and benchmark_avg_ctr > 0:
        # Underperforming if CTR is less than 60% of benchmark average
        underperforming = actual_ctr < (benchmark_avg_ctr * 0.6)

    return CTRDiagnosticResult(
        url=url,
        article_id=article_id,
        position_band=band.value,
        actual_ctr=actual_ctr,
        benchmark_avg_ctr=benchmark_avg_ctr,
        benchmark_median_ctr=benchmark_median_ctr,
        ctr_ratio=ctr_ratio,
        underperforming=underperforming,
        impressions=impressions,
        sample_size_sufficient=sample_sufficient,
    )
