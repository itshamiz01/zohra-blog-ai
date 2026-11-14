"""
Zohra — Ranking Intelligence Engine (Part 8).

Provides:
- Position band assignment
- Ranking trend computation across two comparison windows
- Page-2 opportunity detection (positions 11-20 with impressions)
- Near-top-3 opportunity detection (positions 4-10 with clicks)
- Position volatility assessment
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.schemas.analytics import (
    NearTopOpportunity,
    Page2Opportunity,
    RankingTrend,
    VisibilityTrend,
)

logger = get_logger("analytics.ranking")


def compute_ranking_trend(
    url: str,
    query: str | None,
    current_position: float | None,
    previous_position: float | None,
    current_clicks: int,
    previous_clicks: int,
) -> RankingTrend:
    """Compute ranking trend between two measurement windows."""
    position_delta = None
    if current_position is not None and previous_position is not None:
        position_delta = round(current_position - previous_position, 2)

    click_change_pct = None
    if previous_clicks > 0:
        click_change_pct = round(
            ((current_clicks - previous_clicks) / previous_clicks) * 100, 2
        )

    # Determine trend
    trend = VisibilityTrend.INSUFFICIENT_DATA
    if position_delta is not None:
        if position_delta < -1.0:
            trend = VisibilityTrend.RISING  # Position dropping = ranking improving
        elif position_delta > 1.0:
            trend = VisibilityTrend.DECLINING  # Position rising = ranking dropping
        else:
            trend = VisibilityTrend.STABLE

    return RankingTrend(
        url=url,
        query=query,
        current_position=current_position,
        previous_position=previous_position,
        position_delta=position_delta,
        current_clicks=current_clicks,
        previous_clicks=previous_clicks,
        click_change_pct=click_change_pct,
        trend=trend,
    )


def detect_page2_opportunities(
    page_metrics: list[dict[str, Any]],
    min_impressions: int = 20,
) -> list[Page2Opportunity]:
    """Identify articles ranking on page 2 (positions 11-20) with sufficient impressions.

    These represent content that has earned Google's attention but hasn't
    broken into page 1 yet.
    """
    opportunities = []

    for metric in page_metrics:
        position = metric.get("avg_position")
        impressions = metric.get("impressions", 0)

        if position is None or impressions < min_impressions:
            continue

        if 10.5 <= position <= 20.4:
            distance = round(position - 10.0, 1)
            opportunities.append(
                Page2Opportunity(
                    article_id=metric["article_id"],
                    url=metric["url"],
                    query=metric.get("query", ""),
                    avg_position=position,
                    impressions=impressions,
                    clicks=metric.get("clicks", 0),
                    estimated_position_to_page1=distance,
                )
            )

    # Sort by distance to page 1 (smallest first)
    opportunities.sort(key=lambda x: x.estimated_position_to_page1)
    return opportunities


def detect_near_top_opportunities(
    page_metrics: list[dict[str, Any]],
    min_impressions: int = 30,
) -> list[NearTopOpportunity]:
    """Identify articles ranking in positions 4-10 that could advance to top 3.

    Top 3 positions capture disproportionate click share.
    """
    opportunities = []

    for metric in page_metrics:
        position = metric.get("avg_position")
        impressions = metric.get("impressions", 0)

        if position is None or impressions < min_impressions:
            continue

        if 3.5 <= position <= 10.4:
            distance = round(position - 3.0, 1)
            opportunities.append(
                NearTopOpportunity(
                    article_id=metric["article_id"],
                    url=metric["url"],
                    query=metric.get("query", ""),
                    avg_position=position,
                    impressions=impressions,
                    clicks=metric.get("clicks", 0),
                    distance_to_top3=distance,
                )
            )

    opportunities.sort(key=lambda x: x.distance_to_top3)
    return opportunities


def calculate_position_volatility(
    positions: list[float],
) -> float:
    """Calculate position volatility as the standard deviation of daily positions.

    Higher values indicate unstable rankings. Returns 0.0 for < 3 data points.
    """
    if len(positions) < 3:
        return 0.0

    mean = sum(positions) / len(positions)
    variance = sum((p - mean) ** 2 for p in positions) / len(positions)
    return round(variance ** 0.5, 2)


def classify_lifecycle_stage(
    days_since_publication: int | None,
    impressions: int,
    click_trend: float | None,
) -> str:
    """Classify article lifecycle stage based on age and performance signals."""
    if days_since_publication is None:
        return "UNKNOWN"

    if days_since_publication <= 7:
        return "NEW"
    if days_since_publication <= 30:
        return "RAMPING" if impressions > 0 else "NEW"
    if days_since_publication <= 90:
        if click_trend is not None and click_trend < -0.2:
            return "DECLINING"
        return "ESTABLISHED"
    if days_since_publication <= 180:
        if click_trend is not None and click_trend < -0.3:
            return "DECLINING"
        return "MATURE"
    # 180+ days
    if impressions == 0:
        return "DORMANT"
    if click_trend is not None and click_trend < -0.3:
        return "DECLINING"
    return "MATURE"
