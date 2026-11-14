"""Unit tests for OpportunityScoringEngine."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.constants import ContentAction, OpportunityClassification, OpportunityStatus
from app.opportunity.scoring.engine import OpportunityScoringEngine, ScoringInput


@pytest.fixture
def scoring_engine():
    return OpportunityScoringEngine()


def test_high_priority_opportunity_scoring(scoring_engine):
    inp = ScoringInput(
        trend_score=75.0,
        search_demand_score=80.0,
        intent_strength_score=90.0,
        competition_opportunity_score=75.0,
        site_relevance_score=95.0,
        topical_authority_score=80.0,
        freshness_score=70.0,
        evergreen_score=85.0,
        original_value_score=85.0,
        serp_gap_score=80.0,
        monetization_score=60.0,
        audience_fit_score=90.0,
        cannibalization_risk_score=10.0,
        risk_score=0.0,
        is_official_dominant=False,
        evidence_count=5,
        scoring_profile="default",
    )

    res = scoring_engine.score(inp)
    assert res.opportunity_score >= 75.0
    assert res.confidence_score >= 80.0
    assert res.status == OpportunityStatus.HIGH_PRIORITY
    assert res.priority in (OpportunityClassification.HIGH_PRIORITY, OpportunityClassification.VERY_HIGH_PRIORITY)
    assert len(res.positive_reasons) >= 3


def test_penalty_deductions_applied(scoring_engine):
    inp = ScoringInput(
        trend_score=80.0,
        search_demand_score=80.0,
        site_relevance_score=80.0,
        # High risk and cannibalization flags
        cannibalization_risk_score=80.0,
        recommended_action=ContentAction.CREATE,  # Attempting CREATE on already covered topic
        risk_score=70.0,  # High risk flag
        is_official_dominant=True,
        competition_opportunity_score=20.0,  # Extreme competition
    )

    res = scoring_engine.score(inp)
    assert res.penalties_breakdown.get("cannibalization", 0.0) > 0.0
    assert res.penalties_breakdown.get("risk", 0.0) > 0.0
    assert res.penalties_breakdown.get("extreme_competition", 0.0) > 0.0
    # Score should be substantially penalized
    assert res.opportunity_score < 50.0


def test_expired_opportunity_heavily_penalized(scoring_engine):
    past_time = datetime.now(UTC) - timedelta(hours=2)
    inp = ScoringInput(
        trend_score=90.0,
        search_demand_score=80.0,
        site_relevance_score=90.0,
        expires_at=past_time,
    )

    res = scoring_engine.score(inp)
    assert res.penalties_breakdown.get("expired", 0.0) == 40.0
    assert res.status == OpportunityStatus.REJECTED or res.opportunity_score < 45.0
