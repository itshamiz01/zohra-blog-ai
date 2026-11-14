"""
Zohra — SERP Analyzer.

Extracts strategic SERP features (featured snippets, video dominance, forum prevalence),
evaluates brand dominance, and cross-validates search intent against actual ranking behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.constants import SearchIntent
from app.opportunity.serp.provider import SERPSnapshotData


@dataclass
class SERPAnalysisSummary:
    query: str
    dominant_intent: SearchIntent
    official_domain_dominant: bool
    forum_dominated: bool
    video_dominated: bool
    has_featured_snippet: bool
    has_paa: bool
    top_domains: list[str] = field(default_factory=list)
    competitor_urls: list[str] = field(default_factory=list)
    discovered_questions: list[str] = field(default_factory=list)
    freshness_gap_detected: bool = False
    average_result_age_days: float | None = None


class SERPAnalyzer:
    """Analyzes SERP results to understand competition, feature opportunities, and user demand."""

    def analyze(self, snapshot: SERPSnapshotData) -> SERPAnalysisSummary:
        results = snapshot.results
        if not results:
            return SERPAnalysisSummary(
                query=snapshot.query,
                dominant_intent=snapshot.dominant_intent,
                official_domain_dominant=False,
                forum_dominated=False,
                video_dominated=False,
                has_featured_snippet=False,
                has_paa=False,
            )

        top_3 = results[:3]
        official_in_top_3 = any(r.is_official_domain for r in top_3)

        forum_count = sum(1 for r in results if r.is_forum)
        video_count = sum(1 for r in results if r.result_type.value == "video")

        forum_dominated = forum_count >= 2
        video_dominated = video_count >= 2

        has_featured_snippet = bool(snapshot.features.get("has_featured_snippet"))
        has_paa = bool(snapshot.features.get("has_people_also_ask"))
        paa_questions = snapshot.features.get("people_also_ask", [])

        # Extract competitor domains and URLs (excluding official portal)
        competitor_urls = [r.url for r in results if not r.is_official_domain][:5]
        top_domains = [r.domain for r in results[:5]]

        # Analyze age/freshness of ranking results
        ages: list[float] = []
        now = datetime.now(UTC)
        for r in results:
            if r.published_date:
                age_days = (now - r.published_date).total_seconds() / 86400.0
                ages.append(max(0.0, age_days))

        avg_age = sum(ages) / len(ages) if ages else None
        # Freshness gap: If query contains 2026/new, but ranking results are older than 180 days
        freshness_gap = False
        if avg_age is not None and avg_age > 180 and any(yr in snapshot.query for yr in ("2026", "new", "update")):
            freshness_gap = True

        return SERPAnalysisSummary(
            query=snapshot.query,
            dominant_intent=snapshot.dominant_intent,
            official_domain_dominant=official_in_top_3,
            forum_dominated=forum_dominated,
            video_dominated=video_dominated,
            has_featured_snippet=has_featured_snippet,
            has_paa=has_paa,
            top_domains=top_domains,
            competitor_urls=competitor_urls,
            discovered_questions=paa_questions,
            freshness_gap_detected=freshness_gap,
            average_result_age_days=round(avg_age, 1) if avg_age is not None else None,
        )
