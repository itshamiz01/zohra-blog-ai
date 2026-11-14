"""
Zohra — Freshness Score Calculator.

Computes time-decay score using configurable half-life:
- Breaking tech/news has short half-life (e.g. 12-24h)
- Evergreen research has longer half-life (e.g. 72-168h)
"""

from __future__ import annotations

from datetime import UTC, datetime

# Default half-life in hours per category
CATEGORY_HALF_LIFE_HOURS: dict[str, float] = {
    "Artificial Intelligence": 16.0,
    "Technology": 20.0,
    "Business": 24.0,
    "Science": 72.0,
    "Entertainment": 18.0,
    "Gaming": 24.0,
    "Automotive": 36.0,
    "Finance": 12.0,
    "Health": 48.0,
}


def calculate_freshness_score(
    first_seen_at: datetime,
    last_seen_at: datetime,
    category: str = "Technology",
    now: datetime | None = None,
) -> float:
    """
    Computes Freshness Score [0.0 - 100.0] using exponential half-life decay.
    Considers both age from initial appearance and recency of latest report.
    """
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    if first_seen_at.tzinfo is None:
        first_seen_at = first_seen_at.replace(tzinfo=UTC)
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=UTC)

    half_life = CATEGORY_HALF_LIFE_HOURS.get(category, 24.0)

    # Hours since latest report
    recency_hours = max(0.0, (current_time - last_seen_at).total_seconds() / 3600.0)
    # Hours since initial report
    age_hours = max(0.0, (current_time - first_seen_at).total_seconds() / 3600.0)

    # Primary factor: recency of newest coverage (70% weight)
    recency_decay = 0.5 ** (recency_hours / half_life)

    # Secondary factor: overall event age (30% weight)
    age_decay = 0.5 ** (age_hours / (half_life * 2.0))

    score = 100.0 * ((0.70 * recency_decay) + (0.30 * age_decay))
    return min(100.0, max(0.0, round(score, 2)))


def calculate_freshness(
    first_seen: datetime,
    last_seen: datetime | None = None,
    category: str = "Technology",
    now: datetime | None = None,
) -> float:
    """Convenience alias for freshness calculation."""
    return calculate_freshness_score(
        first_seen_at=first_seen,
        last_seen_at=last_seen or first_seen,
        category=category,
        now=now,
    )
