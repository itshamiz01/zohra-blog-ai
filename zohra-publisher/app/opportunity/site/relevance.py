"""
Zohra — Site Relevance & Topical Authority Scoring.

Evaluates whether a candidate event/topic belongs on the target website profile.
Ensures viral/trending events irrelevant to the site's niche are strictly rejected.
Computes observable topical authority proxies based on existing coverage and topic weights.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.db.models.site_topics import SiteTopic
from app.db.models.sites import Site


@dataclass
class SiteRelevanceResult:
    site_relevance_score: float  # 0 to 100
    topical_authority_score: float  # 0 to 100
    audience_fit_score: float  # 0 to 100
    is_eligible: bool  # False if relevance is below minimum threshold
    matched_topics: list[str]
    rejection_reason: str | None = None


class SiteRelevanceScorer:
    """Calculates site topical relevance, audience alignment, and authority proxy."""

    def __init__(self, min_relevance_threshold: float = 35.0) -> None:
        self.min_relevance_threshold = min_relevance_threshold

    def calculate(
        self,
        site: Site,
        topics: list[SiteTopic],
        event_title: str,
        event_summary: str | None,
        event_category: str,
        entities: list[dict[str, Any]],
        target_audience: list[str] | None = None,
        language: str = "en",
    ) -> SiteRelevanceResult:
        # Check language match
        if site.default_language.lower() != language.lower() and site.default_language.lower() != "all":
            return SiteRelevanceResult(
                site_relevance_score=10.0,
                topical_authority_score=10.0,
                audience_fit_score=10.0,
                is_eligible=False,
                matched_topics=[],
                rejection_reason=f"Language mismatch: site ({site.default_language}) vs event ({language})",
            )

        combined_text = f"{event_title} {event_summary or ''} {event_category}".lower()

        # 1. Match against configured SiteTopics and their relevance weights
        matched_topics: list[str] = []
        topic_scores: list[float] = []
        authority_scores: list[float] = []

        for st in topics:
            tname = st.topic_name.lower()
            slug = st.canonical_slug.lower()
            # Check if topic keyword appears as a whole word/phrase in combined text
            has_tname = bool(re.search(r"\b" + re.escape(tname) + r"\b", combined_text))
            has_slug = len(slug) >= 2 and bool(re.search(r"\b" + re.escape(slug) + r"\b", combined_text))
            has_sig_words = any(
                len(w) > 4 and bool(re.search(r"\b" + re.escape(w) + r"\b", combined_text))
                for w in tname.split()
            )
            if has_tname or has_slug or has_sig_words:
                matched_topics.append(st.topic_name)
                topic_scores.append(st.relevance_weight * 100.0)
                authority_scores.append(st.topical_authority_score)

        # 2. Check site niche & description keywords
        niche_words = re.findall(r"\w+", site.niche.lower())
        niche_matches = sum(
            1 for w in niche_words
            if len(w) > 3 and bool(re.search(r"\b" + re.escape(w) + r"\b", combined_text))
        )
        niche_score = min(100.0, niche_matches * 30.0)

        # 3. Check entity alignments
        entity_matches = 0
        for e in entities:
            ename = e.get("name", "").lower()
            if ename and len(ename) > 2 and (
                any(ename in st.topic_name.lower() for st in topics) or ename in site.niche.lower()
            ):
                entity_matches += 1
        entity_score = min(100.0, entity_matches * 35.0)

        # Compute overall site relevance score
        if topic_scores:
            avg_topic_score = sum(topic_scores) / len(topic_scores)
            relevance = (avg_topic_score * 0.70) + (niche_score * 0.20) + (entity_score * 0.10)
            relevance = max(relevance, avg_topic_score * 0.85)
        else:
            # No configured topics matched — rely solely on niche words
            relevance = niche_score * 0.70 + entity_score * 0.30

        relevance = round(min(100.0, max(0.0, relevance)), 1)

        # 4. Compute topical authority proxy
        auth_proxy = (
            sum(authority_scores) / len(authority_scores)
            if authority_scores
            else 35.0
        )
        auth_proxy = round(min(100.0, max(10.0, auth_proxy)), 1)

        # 5. Audience Fit
        site_audiences = [a.lower() for a in (site.target_audiences or [])]
        if not site_audiences:
            audience_fit = 70.0
        elif not target_audience:
            audience_fit = 60.0
        else:
            # Check overlap
            common = set(site_audiences) & {a.lower() for a in target_audience}
            audience_fit = 95.0 if common else 40.0

        is_eligible = relevance >= self.min_relevance_threshold
        rejection_reason = None if is_eligible else (
            f"Event relevance ({relevance}) is below minimum threshold ({self.min_relevance_threshold}) for site '{site.name}'"
        )

        return SiteRelevanceResult(
            site_relevance_score=relevance,
            topical_authority_score=auth_proxy,
            audience_fit_score=round(audience_fit, 1),
            is_eligible=is_eligible,
            matched_topics=matched_topics,
            rejection_reason=rejection_reason,
        )
