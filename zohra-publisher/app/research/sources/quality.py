"""
Zohra — Source Quality & Valuation Scorer.

Calculates authority, reliability, freshness, relevance, and research_value_score
without relying on popularity alone.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime


class SourceQualityScorer:
    """Calculates multi-dimensional source quality scores for research sources."""

    @classmethod
    def calculate_scores(
        cls,
        source_tier: int,
        source_type: str,
        is_primary_source: bool,
        is_official_source: bool,
        published_at: datetime | None,
        source_trust_score: float | None = None,
        query_overlap_ratio: float = 0.5,
    ) -> dict[str, float]:
        # 1. Authority Score (0-100)
        # Tier 1 = 95, Tier 2 = 80, Tier 3 = 60, Tier 4 = 35
        tier_map = {1: 95.0, 2: 80.0, 3: 60.0, 4: 35.0}
        base_authority = tier_map.get(source_tier, 50.0)

        if is_official_source or is_primary_source:
            base_authority = min(100.0, base_authority + 10.0)

        authority_score = round(base_authority, 1)

        # 2. Reliability Score (0-100)
        if source_trust_score is not None:
            reliability_score = round(source_trust_score, 1)
        else:
            reliability_score = round(base_authority * 0.9, 1)

        # 3. Freshness Score (0-100)
        if published_at:
            now = datetime.now(UTC)
            age_days = max(0.0, (now - published_at).total_seconds() / 86400.0)
            # Exponential decay with 90-day half life
            decay_factor = math.exp(-age_days / 90.0)
            freshness_score = round(max(10.0, 100.0 * decay_factor), 1)
        else:
            freshness_score = 60.0  # Missing date: moderate default

        # 4. Relevance Score (0-100)
        relevance_score = round(min(100.0, max(20.0, query_overlap_ratio * 100.0)), 1)

        # 5. Composite Research Value Score (0-100)
        # Formula: 30% authority + 25% reliability + 20% relevance + 15% freshness + 10% primary boost
        primary_boost = 10.0 if (is_primary_source or is_official_source) else 0.0
        research_value = (
            (authority_score * 0.30)
            + (reliability_score * 0.25)
            + (relevance_score * 0.20)
            + (freshness_score * 0.15)
            + primary_boost
        )

        return {
            "authority_score": authority_score,
            "reliability_score": reliability_score,
            "freshness_score": freshness_score,
            "relevance_score": relevance_score,
            "research_value_score": round(min(100.0, research_value), 1),
        }
