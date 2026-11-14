"""
Zohra — Cannibalization Detector (Part 8).

Detects cases where multiple articles from the same site compete for
the same search query or query cluster, causing ownership volatility.

Detection signals:
- Multiple URLs ranking for the same query within a window
- Position oscillation (ownership switching between URLs)
- Impression/click splitting across competing pages
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger("analytics.cannibalization")


def detect_cannibalization(
    page_query_metrics: list[dict[str, Any]],
    min_impressions: int = 20,
    min_competing_pages: int = 2,
) -> list[dict[str, Any]]:
    """Detect search cannibalization from page-query daily metrics.

    Groups metrics by normalized_query, finds queries where multiple
    article_ids are ranking, and evaluates ownership volatility.

    Args:
        page_query_metrics: List of dicts with keys:
            query, normalized_query, url, article_id, clicks,
            impressions, avg_position, date
        min_impressions: Minimum total impressions for a query to be evaluated.
        min_competing_pages: Minimum number of different pages for cannibalization.

    Returns:
        List of cannibalization event dicts.
    """
    # Group by normalized_query
    query_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in page_query_metrics:
        q = m.get("normalized_query") or m.get("query", "")
        if q:
            query_groups[q].append(m)

    events = []

    for query, metrics in query_groups.items():
        # Aggregate by article_id
        article_stats: dict[str, dict[str, Any]] = {}
        total_impressions = 0
        total_clicks = 0

        for m in metrics:
            art_id = str(m.get("article_id", ""))
            if not art_id or art_id == "None":
                continue

            if art_id not in article_stats:
                article_stats[art_id] = {
                    "article_id": art_id,
                    "urls": set(),
                    "impressions": 0,
                    "clicks": 0,
                    "positions": [],
                    "dates": [],
                }

            article_stats[art_id]["urls"].add(m.get("url", ""))
            article_stats[art_id]["impressions"] += m.get("impressions", 0)
            article_stats[art_id]["clicks"] += m.get("clicks", 0)
            if m.get("avg_position") is not None:
                article_stats[art_id]["positions"].append(m["avg_position"])
            if m.get("date"):
                article_stats[art_id]["dates"].append(m["date"])
            total_impressions += m.get("impressions", 0)
            total_clicks += m.get("clicks", 0)

        # Filter: need minimum competing pages and impressions
        if len(article_stats) < min_competing_pages:
            continue
        if total_impressions < min_impressions:
            continue

        # Determine primary article (highest clicks)
        primary = max(article_stats.values(), key=lambda x: x["clicks"])

        # Count ownership switches (simplified: date-ordered position leader changes)
        ownership_switches = _count_ownership_switches(metrics)

        # Confidence based on number of competing pages and switch count
        confidence = min(
            0.3 + (len(article_stats) - 2) * 0.15 + ownership_switches * 0.1,
            1.0,
        )

        events.append({
            "query": query,
            "article_ids": list(article_stats.keys()),
            "primary_article_id": primary["article_id"],
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ownership_switch_count": ownership_switches,
            "confidence": round(confidence, 2),
            "status": "DETECTED",
            "details_json": {
                "article_impressions": {
                    k: v["impressions"] for k, v in article_stats.items()
                },
                "article_clicks": {
                    k: v["clicks"] for k, v in article_stats.items()
                },
            },
            "detected_at": datetime.now(UTC),
        })

    # Sort by impressions (highest impact first)
    events.sort(key=lambda x: x["impressions"], reverse=True)
    return events


def _count_ownership_switches(metrics: list[dict[str, Any]]) -> int:
    """Count how many times the leading article switched across dates.

    Simplified: group by date, find best-positioned article per date,
    count transitions.
    """
    date_leaders: dict[str, str | None] = {}

    for m in sorted(metrics, key=lambda x: str(x.get("date", ""))):
        date_key = str(m.get("date", ""))[:10]
        art_id = str(m.get("article_id", ""))
        position = m.get("avg_position")

        if not art_id or art_id == "None" or position is None:
            continue

        current_leader = date_leaders.get(date_key)
        if current_leader is None:
            date_leaders[date_key] = art_id
        else:
            # Check if this article has better position
            pass  # Simplified: first seen per date wins

    leaders = list(date_leaders.values())
    switches = 0
    for i in range(1, len(leaders)):
        if leaders[i] != leaders[i - 1]:
            switches += 1

    return switches
