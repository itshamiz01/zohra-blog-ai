"""
Zohra — Part 9 Optimization Candidate Package Generator (Part 8).

Generates prioritized OptimizationCandidatePackage objects from
Part 8 diagnostic findings. These are handed to Part 9 for
autonomous investigation and potential content optimization.

Part 8 boundary: ONLY diagnoses and recommends. NEVER modifies content.
"""

from __future__ import annotations

import hashlib
import uuid

from app.core.logging import get_logger
from app.schemas.analytics import (
    OpportunityCandidateType,
    OptimizationCandidatePackage,
    SearchMetrics,
)

logger = get_logger("analytics.opportunity_generator")


def generate_candidate_id(
    site_id: uuid.UUID,
    article_id: uuid.UUID,
    candidate_type: str,
    query: str = "",
) -> str:
    """Generate a deterministic candidate ID from key dimensions."""
    raw = f"{site_id}:{article_id}:{candidate_type}:{query}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def generate_low_ctr_opportunity(
    site_id: uuid.UUID,
    article_id: uuid.UUID,
    url: str,
    actual_ctr: float | None,
    benchmark_avg_ctr: float,
    avg_position: float | None,
    impressions: int,
    clicks: int,
    query: str = "",
    content_type: str | None = None,
    topic: str | None = None,
    article_age: int | None = None,
) -> OptimizationCandidatePackage:
    """Generate a Low CTR optimization candidate."""
    candidate_id = generate_candidate_id(site_id, article_id, "LOW_CTR", query)

    # Priority: high impressions + low CTR = high opportunity
    priority = min(
        (impressions / 100.0) * (1.0 - (actual_ctr or 0) / max(benchmark_avg_ctr, 0.001)) * 10,
        100.0,
    )

    return OptimizationCandidatePackage(
        candidate_id=candidate_id,
        site_id=site_id,
        article_id=article_id,
        candidate_type=OpportunityCandidateType.LOW_CTR,
        priority_score=round(priority, 2),
        confidence=0.7 if impressions >= 200 else 0.4,
        observed_problem=(
            f"CTR ({actual_ctr:.2%} actual) is significantly below site benchmark "
            f"({benchmark_avg_ctr:.2%}) for this position band."
            if actual_ctr is not None
            else "CTR data unavailable despite sufficient impressions."
        ),
        evidence={
            "url": url,
            "actual_ctr": actual_ctr,
            "benchmark_avg_ctr": benchmark_avg_ctr,
            "impressions": impressions,
            "query": query,
        },
        current_metrics=SearchMetrics(
            clicks=clicks,
            impressions=impressions,
            ctr=actual_ctr,
            avg_position=avg_position,
        ),
        affected_queries=[query] if query else [],
        article_age=article_age,
        content_type=content_type,
        topic=topic,
        possible_causes=[
            "Title may not match searcher intent",
            "Meta description may not be compelling",
            "SERP features may be capturing clicks",
            "Rich snippets or featured answers may be present",
        ],
        recommended_investigation=[
            "Review title and meta description against top-ranking competitors",
            "Check for SERP feature presence (featured snippets, PAA)",
            "Analyze query intent alignment with page content",
        ],
    )


def generate_page2_opportunity(
    site_id: uuid.UUID,
    article_id: uuid.UUID,
    url: str,
    query: str,
    avg_position: float,
    impressions: int,
    clicks: int,
    content_type: str | None = None,
    topic: str | None = None,
    article_age: int | None = None,
) -> OptimizationCandidatePackage:
    """Generate a Page 2 opportunity candidate."""
    candidate_id = generate_candidate_id(site_id, article_id, "PAGE_2_OPPORTUNITY", query)

    # Priority: closer to page 1 + more impressions = higher priority
    distance = avg_position - 10.0
    priority = min(
        (20.0 - distance) * (impressions / 50.0),
        100.0,
    )

    return OptimizationCandidatePackage(
        candidate_id=candidate_id,
        site_id=site_id,
        article_id=article_id,
        candidate_type=OpportunityCandidateType.PAGE_2_OPPORTUNITY,
        priority_score=round(max(priority, 1.0), 2),
        confidence=0.6,
        observed_problem=(
            f"Article ranks at position {avg_position:.1f} for query '{query}' — "
            f"page 2 with {impressions:,} impressions."
        ),
        evidence={
            "url": url,
            "query": query,
            "avg_position": avg_position,
            "impressions": impressions,
            "distance_to_page1": round(distance, 1),
        },
        current_metrics=SearchMetrics(
            clicks=clicks, impressions=impressions, avg_position=avg_position,
        ),
        affected_queries=[query],
        article_age=article_age,
        content_type=content_type,
        topic=topic,
        possible_causes=[
            "Content may lack depth or comprehensiveness",
            "Internal linking to this page may be insufficient",
            "Domain authority may be lower than competitors for this query",
        ],
        recommended_investigation=[
            "Compare content depth and structure with page-1 competitors",
            "Evaluate internal linking opportunities from high-authority pages",
            "Assess whether content freshness could improve ranking",
        ],
    )


def generate_cannibalization_opportunity(
    site_id: uuid.UUID,
    primary_article_id: uuid.UUID,
    query: str,
    competing_article_ids: list[str],
    impressions: int,
    clicks: int,
    ownership_switch_count: int,
    topic: str | None = None,
) -> OptimizationCandidatePackage:
    """Generate a cannibalization opportunity candidate."""
    candidate_id = generate_candidate_id(
        site_id, primary_article_id, "CANNIBALIZATION", query
    )

    priority = min(
        impressions / 20.0 * (1 + ownership_switch_count * 0.5),
        100.0,
    )

    return OptimizationCandidatePackage(
        candidate_id=candidate_id,
        site_id=site_id,
        article_id=primary_article_id,
        candidate_type=OpportunityCandidateType.CANNIBALIZATION,
        priority_score=round(priority, 2),
        confidence=min(0.4 + ownership_switch_count * 0.1, 0.9),
        observed_problem=(
            f"{len(competing_article_ids)} articles competing for query '{query}' "
            f"with {ownership_switch_count} ownership switches."
        ),
        evidence={
            "query": query,
            "competing_articles": competing_article_ids,
            "impressions": impressions,
            "clicks": clicks,
            "ownership_switches": ownership_switch_count,
        },
        current_metrics=SearchMetrics(clicks=clicks, impressions=impressions),
        affected_queries=[query],
        topic=topic,
        possible_causes=[
            "Multiple pages target overlapping topic areas",
            "Internal linking sends mixed signals about the canonical page",
            "Content differentiation between competing pages is unclear",
        ],
        recommended_investigation=[
            "Review competing pages for content overlap",
            "Consider content consolidation or clear topic differentiation",
            "Evaluate internal linking to establish clear primary page",
        ],
    )


def prioritize_candidates(
    candidates: list[OptimizationCandidatePackage],
    max_candidates: int = 50,
) -> list[OptimizationCandidatePackage]:
    """Sort and cap candidates by priority score."""
    sorted_candidates = sorted(
        candidates,
        key=lambda c: c.priority_score,
        reverse=True,
    )
    return sorted_candidates[:max_candidates]
