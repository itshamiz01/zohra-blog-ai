"""Unit tests for CompetitionAnalyzer and Content Gap detection."""

from datetime import UTC, datetime

import pytest

from app.core.constants import SearchIntent, SERPResultType
from app.opportunity.competition.analyzer import CompetitionAnalyzer
from app.opportunity.serp.provider import NormalizedSERPResult, SERPSnapshotData


@pytest.fixture
def analyzer():
    return CompetitionAnalyzer()


def test_competition_score_with_official_portal_dominance(analyzer):
    results = [
        NormalizedSERPResult(
            position=1,
            url="https://openai.com/login",
            domain="openai.com",
            title="ChatGPT Login — Official Portal",
            snippet="Log into your OpenAI account.",
            result_type=SERPResultType.ORGANIC,
            is_official_domain=True,
        ),
        NormalizedSERPResult(
            position=2,
            url="https://techcrunch.com/chatgpt-portal",
            domain="techcrunch.com",
            title="ChatGPT Overview",
            snippet="Overview of login and account features.",
            result_type=SERPResultType.ORGANIC,
        ),
    ]

    snapshot = SERPSnapshotData(
        query="chatgpt login",
        query_hash="hash123",
        provider="mock",
        country="global",
        language="en",
        device="desktop",
        total_results_estimate=1000000,
        dominant_intent=SearchIntent.NAVIGATIONAL,
        intent_alignment_score=0.95,
        features={},
        results=results,
        retrieved_at=datetime.now(UTC),
    )

    res = analyzer.analyze(snapshot)
    assert res.competition_score >= 65.0  # High competition due to official portal dominance
    assert res.competition_opportunity_score <= 35.0


def test_structural_content_gaps_identified(analyzer):
    # SERP where competitors discuss features but omit pricing numbers and step-by-step workflow
    results = [
        NormalizedSERPResult(
            position=1,
            url="https://techblog.com/model-x",
            domain="techblog.com",
            title="Model X Overview and Announcement",
            snippet="Model X introduces revolutionary multimodal capabilities with advanced neural networks.",
            result_type=SERPResultType.ORGANIC,
        ),
        NormalizedSERPResult(
            position=2,
            url="https://news.com/model-x",
            domain="news.com",
            title="What is Model X?",
            snippet="A look at what the new architecture promises for enterprise AI.",
            result_type=SERPResultType.ORGANIC,
        ),
    ]

    snapshot = SERPSnapshotData(
        query="how to use model x tutorial and pricing",
        query_hash="hash456",
        provider="mock",
        country="global",
        language="en",
        device="desktop",
        total_results_estimate=500000,
        dominant_intent=SearchIntent.TUTORIAL,
        intent_alignment_score=0.90,
        features={},
        results=results,
        retrieved_at=datetime.now(UTC),
    )

    res = analyzer.analyze(snapshot)
    gap_types = [g.gap_type for g in res.gaps]

    # Structural gaps should be detected
    assert "missing_pricing" in gap_types
    assert "lack_of_workflow" in gap_types
    assert res.information_gain_score >= 50.0


def test_zero_serp_emerging_topic_handling(analyzer):
    snapshot = SERPSnapshotData(
        query="brand new unheard model query",
        query_hash="hash789",
        provider="mock",
        country="global",
        language="en",
        device="desktop",
        total_results_estimate=0,
        dominant_intent=SearchIntent.INFORMATIONAL,
        intent_alignment_score=0.70,
        features={},
        results=[],
        retrieved_at=datetime.now(UTC),
    )

    res = analyzer.analyze(snapshot)
    assert res.competition_score == 20.0  # Very low competition
    assert res.competition_opportunity_score == 80.0
    assert res.information_gain_score >= 80.0
