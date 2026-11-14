"""
Section 100 & 115: Deterministic Validation Simulation for Scenarios A through J.

Validates that Zohra's Content Opportunity Intelligence Engine correctly
decides between REJECT, HIGH PRIORITY, UPDATE, CREATE, and handles missing metrics,
rapid expirations, and high-risk flags accurately.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.constants import (
    ContentAction,
    OpportunityClassification,
    OpportunityStatus,
    SearchIntent,
)
from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.site_content import SiteContent
from app.db.models.site_topics import SiteTopic
from app.db.models.sites import Site
from app.discovery.handoff import QualifiedEventHandoff
from app.opportunity.keywords.expander import KeywordExpander
from app.opportunity.pipeline import OpportunityPipeline
from app.opportunity.scoring.engine import OpportunityScoringEngine, ScoringInput
from app.opportunity.site.cannibalization import CannibalizationDetector


@pytest.fixture
async def setup_test_site(db_session):
    site = Site(
        id=uuid.uuid4(),
        name="AI Automation & Creator Publication",
        domain="aiautomationcreators.com",
        default_language="en",
        primary_country="global",
        niche="Artificial Intelligence, Developer Tools, Software Automation & Creators",
        description="Comprehensive guides, tutorials, and benchmarks on generative AI and automation tools.",
        target_audiences=["creators", "developers", "automation engineers"],
        enabled=True,
    )
    db_session.add(site)
    await db_session.flush()

    topics = [
        ("Artificial Intelligence", "ai", 1.0, 80.0),
        ("Developer Tools", "dev-tools", 0.95, 75.0),
        ("Software Automation", "automation", 0.90, 70.0),
        ("Content Creation", "content-creation", 0.85, 65.0),
    ]
    for tname, slug, rel, auth in topics:
        st = SiteTopic(
            site_id=site.id,
            topic_name=tname,
            canonical_slug=slug,
            relevance_weight=rel,
            topical_authority_score=auth,
            historical_post_count=15,
        )
        db_session.add(st)
    await db_session.commit()
    return site


@pytest.mark.asyncio
async def test_scenario_a_huge_trend_irrelevant_to_site_is_rejected(db_session, setup_test_site):
    """Scenario A: Huge viral trend, but irrelevant to site niche -> REJECT."""
    pipeline = OpportunityPipeline()
    handoff = QualifiedEventHandoff(
        event_id=str(uuid.uuid4()),
        canonical_title="Celebrity World Tour Breaks Global Box Office Records",
        summary="Entertainment tour achieves unprecedented ticket sales across international stadiums.",
        category="Entertainment",
        event_type="announcement",
        language="en",
        countries=["global"],
        trend_score=98.0,
        velocity_score=30.0,
        confidence_score=95.0,
        entities=[{"name": "Pop Star", "type": "person"}],
    )

    packages = await pipeline.process_event(session=db_session, event_handoff=handoff, site_id=setup_test_site.id)
    # Irrelevant event must produce 0 qualified publishing packages
    assert len(packages) == 0

    # Verify audit record shows REJECTED status
    opps = list((await db_session.execute(select(ContentOpportunity))).scalars().all())
    assert any(o.status == OpportunityStatus.REJECTED.value for o in opps)


@pytest.mark.asyncio
async def test_scenario_b_moderate_trend_niche_relevance_weak_competition(db_session, setup_test_site):
    """Scenario B: Moderate trend, excellent niche relevance and weak competition -> HIGH PRIORITY."""
    scoring_engine = OpportunityScoringEngine()
    inp = ScoringInput(
        trend_score=68.0,
        search_demand_score=78.0,
        intent_strength_score=92.0,
        competition_opportunity_score=80.0,  # Weak competition (forum-dominated)
        site_relevance_score=95.0,  # Strong niche fit
        topical_authority_score=75.0,
        freshness_score=70.0,
        evergreen_score=85.0,
        original_value_score=88.0,
        serp_gap_score=82.0,
        monetization_score=65.0,
        audience_fit_score=95.0,
        cannibalization_risk_score=5.0,
        risk_score=0.0,
        evidence_count=5,
    )

    res = scoring_engine.score(inp)
    assert res.opportunity_score >= 75.0
    assert res.status == OpportunityStatus.HIGH_PRIORITY
    assert res.priority in (OpportunityClassification.HIGH_PRIORITY, OpportunityClassification.VERY_HIGH_PRIORITY)


@pytest.mark.asyncio
async def test_scenario_c_huge_volume_competitive_navigational_query():
    """Scenario C: Huge volume, but strictly navigational query dominated by official login portal -> LOW / REJECT."""
    scoring_engine = OpportunityScoringEngine()
    inp = ScoringInput(
        trend_score=90.0,
        search_demand_score=95.0,
        intent_strength_score=80.0,
        competition_opportunity_score=15.0,  # Fierce competition
        site_relevance_score=60.0,
        topical_authority_score=50.0,
        freshness_score=50.0,
        evergreen_score=40.0,
        original_value_score=20.0,  # Cannot add original value to someone else's login page
        serp_gap_score=10.0,
        monetization_score=20.0,
        audience_fit_score=50.0,
        is_official_dominant=True,  # Official portal dominates
        cannibalization_risk_score=0.0,
        risk_score=0.0,
    )

    res = scoring_engine.score(inp)
    # Severe competition penalty applied
    assert res.penalties_breakdown.get("extreme_competition", 0.0) > 0.0
    assert res.opportunity_score < 40.0
    assert res.status == OpportunityStatus.REJECTED


@pytest.mark.asyncio
async def test_scenario_d_emerging_zero_volume_keyword_retains_opportunity():
    """Scenario D: New product with zero historical search volume -> Trend velocity compensates."""
    expander = KeywordExpander()
    candidates = expander.discover_and_expand(
        event_title="Midjourney Releases V7 Photorealistic Engine",
        event_summary="New generative visual architecture announced.",
        entities=[{"name": "Midjourney V7", "type": "product"}],
        event_type="launch",
        category="Technology",
        trend_score=92.0,
        velocity_score=22.0,
    )

    top = candidates[0]
    # Volume is None (NOT 0)
    assert top.search_volume is None
    # Demand score is strong due to trend velocity
    assert top.search_demand_score >= 65.0


@pytest.mark.asyncio
async def test_scenario_e_existing_identical_intent_triggers_update(setup_test_site, db_session):
    """Scenario E: Excellent keyword but existing article already targets identical intent -> UPDATE, not CREATE."""
    existing_article = SiteContent(
        id=uuid.uuid4(),
        site_id=setup_test_site.id,
        url="https://aiautomationcreators.com/how-to-use-midjourney-v7",
        slug="how-to-use-midjourney-v7",
        title="How to Use Midjourney V7: Full Step-by-Step Beginner Guide",
        primary_topic="Midjourney",
        primary_keyword="how to use midjourney v7",
        primary_intent="tutorial",
    )
    db_session.add(existing_article)
    await db_session.commit()

    detector = CannibalizationDetector()
    res = detector.evaluate(
        candidate_keyword="how to use midjourney v7 tutorial",
        candidate_intent=SearchIntent.TUTORIAL,
        candidate_topic="How to Use Midjourney V7",
        existing_articles=[existing_article],
    )

    assert res.recommended_action == ContentAction.UPDATE
    assert res.target_content_id == existing_article.id
    assert res.same_intent_detected is True


@pytest.mark.asyncio
async def test_scenario_f_similar_keyword_distinct_intent_triggers_create(setup_test_site, db_session):
    """Scenario F: Same entity but genuinely different intent -> CREATE."""
    existing_article = SiteContent(
        id=uuid.uuid4(),
        site_id=setup_test_site.id,
        url="https://aiautomationcreators.com/what-is-midjourney-v7",
        slug="what-is-midjourney-v7",
        title="What is Midjourney V7? Architecture & Features",
        primary_topic="Midjourney",
        primary_keyword="what is midjourney v7",
        primary_intent="informational",
    )
    db_session.add(existing_article)
    await db_session.commit()

    detector = CannibalizationDetector()
    # Candidate targets PRICING (commercial investigation), while existing is architectural explainer (informational)
    res = detector.evaluate(
        candidate_keyword="midjourney v7 pricing and subscription plans",
        candidate_intent=SearchIntent.COMMERCIAL_INVESTIGATION,
        candidate_topic="Midjourney V7 Pricing Plans",
        existing_articles=[existing_article],
    )

    assert res.recommended_action == ContentAction.CREATE
    assert res.cannibalization_risk_score <= 20.0
    assert res.same_intent_detected is False


@pytest.mark.asyncio
async def test_scenario_g_missing_cpc_remains_null():
    """Scenario G: Commercial keyword with missing CPC -> CPC remains NULL, never faked."""
    expander = KeywordExpander()
    candidates = expander.discover_and_expand(
        event_title="Anthropic Launches Claude 3.5 Sonnet API",
        event_summary="Pricing announced per million tokens.",
        entities=[{"name": "Claude 3.5 Sonnet", "type": "product"}],
        event_type="launch",
        category="Technology",
        trend_score=85.0,
    )

    commercial_cands = [c for c in candidates if c.intent == SearchIntent.COMMERCIAL_INVESTIGATION]
    assert len(commercial_cands) > 0
    for c in commercial_cands:
        assert c.cpc is None  # Strict NULL enforcement
        assert c.cpc_source is None


@pytest.mark.asyncio
async def test_scenario_h_breaking_event_short_expiration():
    """Scenario H: Breaking event that expires quickly -> high priority + short expiration window."""
    scoring_engine = OpportunityScoringEngine()
    future_expire = datetime.now(UTC) + timedelta(hours=6)
    inp = ScoringInput(
        trend_score=95.0,
        search_demand_score=85.0,
        intent_strength_score=80.0,
        competition_opportunity_score=80.0,
        site_relevance_score=95.0,
        topical_authority_score=70.0,
        freshness_score=95.0,
        evergreen_score=20.0,
        original_value_score=80.0,
        serp_gap_score=75.0,
        monetization_score=40.0,
        audience_fit_score=90.0,
        scoring_profile="breaking_news",
        expires_at=future_expire,
    )

    res = scoring_engine.score(inp)
    assert res.opportunity_score >= 75.0
    assert res.status == OpportunityStatus.HIGH_PRIORITY


@pytest.mark.asyncio
async def test_scenario_i_evergreen_tutorial_opportunity():
    """Scenario I: Evergreen tutorial opportunity -> high evergreen score, long-term opportunity."""
    scoring_engine = OpportunityScoringEngine()
    inp = ScoringInput(
        trend_score=50.0,
        search_demand_score=85.0,
        intent_strength_score=95.0,
        competition_opportunity_score=70.0,
        site_relevance_score=95.0,
        topical_authority_score=80.0,
        freshness_score=50.0,
        evergreen_score=95.0,
        original_value_score=90.0,
        serp_gap_score=85.0,
        monetization_score=60.0,
        audience_fit_score=95.0,
        scoring_profile="evergreen",
    )

    res = scoring_engine.score(inp)
    assert res.opportunity_score >= 80.0
    assert res.priority in (OpportunityClassification.HIGH_PRIORITY, OpportunityClassification.VERY_HIGH_PRIORITY)


@pytest.mark.asyncio
async def test_scenario_j_high_risk_topic_propagates_flags():
    """Scenario J: High-risk topic -> risk flags propagated, risk penalty applied."""
    scoring_engine = OpportunityScoringEngine()
    inp = ScoringInput(
        trend_score=85.0,
        search_demand_score=80.0,
        intent_strength_score=80.0,
        competition_opportunity_score=70.0,
        site_relevance_score=85.0,
        risk_score=75.0,  # High risk flag (financial / legal claims)
        evidence_count=2,
    )

    res = scoring_engine.score(inp)
    assert res.penalties_breakdown.get("risk", 0.0) >= 20.0
    # Confidence is penalized when risk is high
    assert res.confidence_score <= 60.0
