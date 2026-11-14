"""Unit tests for KeywordExpander and KeywordClusteringEngine."""

import pytest

from app.core.constants import SearchIntent
from app.opportunity.clustering.engine import KeywordClusteringEngine
from app.opportunity.keywords.expander import KeywordCandidate, KeywordExpander


@pytest.fixture
def expander():
    return KeywordExpander()


@pytest.fixture
def clustering_engine():
    return KeywordClusteringEngine(serp_overlap_threshold=0.40)


def test_normalization_preserves_intent_distinctions(expander):
    n1 = expander.normalize("ChatGPT pricing")
    n2 = expander.normalize("ChatGPT API pricing")

    assert n1 != n2
    assert "api" in n2
    assert "pricing" in n1 and "pricing" in n2


def test_keyword_expansion_leaves_missing_metrics_as_none(expander):
    candidates = expander.discover_and_expand(
        event_title="Runway Launches Gen-3 Alpha AI Video Model",
        event_summary="New generative video model announced with realistic physics and camera controls.",
        entities=[{"name": "Runway", "type": "organization"}, {"name": "Gen-3 Alpha", "type": "product"}],
        event_type="launch",
        category="Technology",
        trend_score=85.0,
        velocity_score=12.0,
    )

    assert len(candidates) > 0
    for c in candidates:
        # STRICT ANTI-HALLUCINATION: external search volume and cpc MUST be None
        assert c.search_volume is None
        assert c.cpc is None
        assert c.search_demand_score > 0.0  # Internal score is populated


def test_zero_volume_emerging_queries_have_viable_demand(expander):
    # Brand new model released 10 mins ago with zero search history
    candidates = expander.discover_and_expand(
        event_title="DeepSeek Announces V3 Architecture Today",
        event_summary="Massive open weights release.",
        entities=[{"name": "DeepSeek V3", "type": "product"}],
        event_type="announcement",
        category="Technology",
        trend_score=95.0,
        velocity_score=25.0,
    )

    top_cand = candidates[0]
    # Emerging query demand should be strong due to trend velocity
    assert top_cand.search_demand_score >= 65.0
    assert top_cand.search_volume is None


def test_clustering_separates_distinct_search_intents(clustering_engine):
    kws = [
        KeywordCandidate(
            keyword="how to use model x",
            normalized_keyword="how to use model x",
            intent=SearchIntent.TUTORIAL,
            secondary_intent=None,
            intent_confidence=0.9,
            intent_strength_score=90.0,
            search_demand_score=85.0,
        ),
        KeywordCandidate(
            keyword="model x tutorial for beginners",
            normalized_keyword="model x tutorial for beginner",
            intent=SearchIntent.TUTORIAL,
            secondary_intent=None,
            intent_confidence=0.9,
            intent_strength_score=92.0,
            search_demand_score=80.0,
        ),
        KeywordCandidate(
            keyword="model x pricing and plans",
            normalized_keyword="model x pricing and plan",
            intent=SearchIntent.COMMERCIAL_INVESTIGATION,
            secondary_intent=None,
            intent_confidence=0.9,
            intent_strength_score=88.0,
            search_demand_score=82.0,
        ),
    ]

    clusters = clustering_engine.cluster(kws)
    assert len(clusters) == 2  # Tutorial cluster and Commercial/Pricing cluster are strictly separated

    tutorial_cluster = next(c for c in clusters if c.primary_intent == SearchIntent.TUTORIAL)
    pricing_cluster = next(c for c in clusters if c.primary_intent == SearchIntent.COMMERCIAL_INVESTIGATION)

    assert len(tutorial_cluster.members) == 2
    assert len(pricing_cluster.members) == 1


def test_serp_overlap_calculation(clustering_engine):
    urls_a = [f"https://domain{i}.com/page" for i in range(10)]
    urls_b = [f"https://domain{i}.com/page" for i in range(5)] + [f"https://other{i}.com/page" for i in range(5)]

    overlap = clustering_engine.calculate_serp_overlap(urls_a, urls_b)
    # 5 common out of 15 total unique URLs -> 5/15 = 0.333
    assert 0.30 <= overlap <= 0.35
