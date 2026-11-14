"""
Unit tests for Source Intelligence, Suitability, Quality, and Independence.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.research.sources.independence import SourceIndependenceEngine
from app.research.sources.quality import SourceQualityScorer
from app.research.sources.suitability import SourceSuitabilityEngine
from app.schemas.research import SourceType


def test_source_suitability_matrix():
    # Official docs are preferred for software technical capability
    doc_score = SourceSuitabilityEngine.get_suitability_score(
        target_category="technical",
        source_type=SourceType.OFFICIAL_DOCUMENTATION.value,
        is_primary_source=True,
    )
    forum_score = SourceSuitabilityEngine.get_suitability_score(
        target_category="technical",
        source_type=SourceType.COMMUNITY_FORUM.value,
        is_primary_source=False,
    )
    assert doc_score > forum_score
    assert doc_score >= 1.0  # 1.0 maxed with primary boost

    # Community forums preferred for user experience/sentiment
    forum_ux = SourceSuitabilityEngine.get_suitability_score(
        target_category="user_experience",
        source_type=SourceType.COMMUNITY_FORUM.value,
        is_primary_source=False,
    )
    doc_ux = SourceSuitabilityEngine.get_suitability_score(
        target_category="user_experience",
        source_type=SourceType.OFFICIAL_DOCUMENTATION.value,
        is_primary_source=False,
    )
    assert forum_ux > doc_ux


def test_source_quality_scorer_tier_and_freshness():
    now = datetime.now(UTC)
    fresh_date = now - timedelta(days=2)
    stale_date = now - timedelta(days=365)

    fresh_tier1 = SourceQualityScorer.calculate_scores(
        source_tier=1,
        source_type="official_documentation",
        is_primary_source=True,
        is_official_source=True,
        published_at=fresh_date,
    )
    stale_tier4 = SourceQualityScorer.calculate_scores(
        source_tier=4,
        source_type="community_forum",
        is_primary_source=False,
        is_official_source=False,
        published_at=stale_date,
    )

    assert fresh_tier1["authority_score"] > stale_tier4["authority_score"]
    assert fresh_tier1["freshness_score"] > stale_tier4["freshness_score"]
    assert fresh_tier1["research_value_score"] > 80.0
    assert stale_tier4["research_value_score"] < 50.0


def test_source_independence_groups_syndication():
    # Two articles with identical wire copy
    text_wire = (
        "SAN FRANCISCO, Oct 1 (PR Newswire) -- Model X today officially launched its next generation "
        "video intelligence platform featuring automated 4K rendering and enterprise video workflows. "
        "The model is priced at twenty dollars per month."
    )
    source_a = {
        "id": "src_1",
        "url": "https://tech-wire-news.com/model-x-launch",
        "publisher": "Tech Wire",
        "text": text_wire,
    }
    source_b = {
        "id": "src_2",
        "url": "https://syndicated-feeds.com/model-x-pr",
        "publisher": "Syndicated Feeds",
        "text": text_wire,
    }
    source_c = {
        "id": "src_3",
        "url": "https://independent-creator.com/my-thoughts-model-x",
        "publisher": "Independent Creator",
        "text": "I tested Model X in my studio for 3 days. The rendering is fast but requires a good GPU.",
    }

    groups = SourceIndependenceEngine.detect_independence_groups([source_a, source_b, source_c])

    # Source A and Source B share the same wire copy and attribution -> same independence group
    assert groups["src_1"] == groups["src_2"]
    # Source C is independent reporting -> distinct group
    assert groups["src_3"] != groups["src_1"]


def test_circular_citation_detection():
    # A cites B, B cites C, C cites A
    citations = [("src_A", "src_B"), ("src_B", "src_C"), ("src_C", "src_A")]
    loops = SourceIndependenceEngine.detect_circular_citations(citations)
    assert len(loops) > 0
