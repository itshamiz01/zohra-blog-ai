"""Unit tests for SiteRelevanceScorer and CannibalizationDetector."""

import uuid

import pytest

from app.core.constants import ContentAction, SearchIntent
from app.db.models.site_content import SiteContent
from app.db.models.site_topics import SiteTopic
from app.db.models.sites import Site
from app.opportunity.site.cannibalization import CannibalizationDetector
from app.opportunity.site.relevance import SiteRelevanceScorer


@pytest.fixture
def relevance_scorer():
    return SiteRelevanceScorer(min_relevance_threshold=35.0)


@pytest.fixture
def cannibalization_detector():
    return CannibalizationDetector(similarity_threshold=0.70)


@pytest.fixture
def ai_site():
    return Site(
        id=uuid.uuid4(),
        name="AI Tech Hub",
        domain="aitechhub.com",
        default_language="en",
        primary_country="global",
        niche="Artificial Intelligence, Developer Tools and Software Automation",
        description="Covering cutting-edge AI models, tutorials, and development.",
        target_audiences=["developers", "engineers"],
        enabled=True,
    )


@pytest.fixture
def ai_topics(ai_site):
    return [
        SiteTopic(
            id=uuid.uuid4(),
            site_id=ai_site.id,
            topic_name="Artificial Intelligence",
            canonical_slug="ai",
            relevance_weight=1.0,
            topical_authority_score=80.0,
        ),
        SiteTopic(
            id=uuid.uuid4(),
            site_id=ai_site.id,
            topic_name="Machine Learning",
            canonical_slug="ml",
            relevance_weight=0.95,
            topical_authority_score=75.0,
        ),
    ]


def test_scenario_a_irrelevant_viral_event_is_rejected(relevance_scorer, ai_site, ai_topics):
    # Taylor Swift global concert update with huge trend score
    res = relevance_scorer.calculate(
        site=ai_site,
        topics=ai_topics,
        event_title="Taylor Swift Announces Massive 2026 World Tour Dates",
        event_summary="Pop superstar reveals stadium concert schedule across Europe and North America.",
        event_category="Entertainment",
        entities=[{"name": "Taylor Swift", "type": "person"}],
    )

    assert not res.is_eligible
    assert res.site_relevance_score < 35.0
    assert "below minimum threshold" in (res.rejection_reason or "")


def test_relevant_niche_topic_is_accepted(relevance_scorer, ai_site, ai_topics):
    res = relevance_scorer.calculate(
        site=ai_site,
        topics=ai_topics,
        event_title="OpenAI Releases GPT-5 with Advanced Autonomous Agent Reasoning",
        event_summary="Breakthrough in artificial intelligence machine learning model architecture.",
        event_category="Technology",
        entities=[{"name": "OpenAI", "type": "organization"}, {"name": "GPT-5", "type": "product"}],
    )

    assert res.is_eligible
    assert res.site_relevance_score >= 80.0
    assert res.topical_authority_score >= 70.0


def test_scenario_e_identical_intent_triggers_update(cannibalization_detector, ai_site):
    existing = [
        SiteContent(
            id=uuid.uuid4(),
            site_id=ai_site.id,
            url="https://aitechhub.com/how-to-use-claude-3-tutorial",
            slug="how-to-use-claude-3-tutorial",
            title="How to Use Claude 3 for Beginners Tutorial",
            primary_topic="Claude",
            primary_keyword="how to use claude 3",
            primary_intent="tutorial",
            language="en",
        )
    ]

    res = cannibalization_detector.evaluate(
        candidate_keyword="how to use claude 3 step by step tutorial",
        candidate_intent=SearchIntent.TUTORIAL,
        candidate_topic="How to Use Claude 3",
        existing_articles=existing,
    )

    # Identical intent on existing article -> UPDATE instead of CREATE
    assert res.recommended_action == ContentAction.UPDATE
    assert res.cannibalization_risk_score >= 70.0
    assert res.target_content_id == existing[0].id
    assert res.same_intent_detected is True


def test_scenario_f_distinct_intent_triggers_create(cannibalization_detector, ai_site):
    existing = [
        SiteContent(
            id=uuid.uuid4(),
            site_id=ai_site.id,
            url="https://aitechhub.com/what-is-claude-3-architecture",
            slug="what-is-claude-3-architecture",
            title="What is Claude 3? Architecture & Model Capabilities",
            primary_topic="Claude",
            primary_keyword="what is claude 3",
            primary_intent="informational",
            language="en",
        )
    ]

    # Candidate targets TUTORIAL intent for the same entity
    res = cannibalization_detector.evaluate(
        candidate_keyword="how to use claude 3 tutorial",
        candidate_intent=SearchIntent.TUTORIAL,
        candidate_topic="Claude 3 Tutorial for Beginners",
        existing_articles=existing,
    )

    # Distinct intent -> CREATE approved as complementary content
    assert res.recommended_action == ContentAction.CREATE
    assert res.cannibalization_risk_score <= 20.0
    assert res.same_intent_detected is False
