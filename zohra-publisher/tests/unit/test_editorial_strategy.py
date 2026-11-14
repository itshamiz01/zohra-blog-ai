"""
Unit tests for ContentStrategist and Intent Adaptation (Part 5).
"""

from __future__ import annotations

import pytest

from app.editorial.strategy.strategist import ContentStrategist
from app.schemas.editorial import ContentType
from app.schemas.research import (
    FinalResearchPackage,
    ResearchQuestionsSummary,
    VerifiedFactHandoff,
    WriterInstructions,
)


@pytest.fixture
def mock_research_package() -> FinalResearchPackage:
    facts = [
        VerifiedFactHandoff(
            claim_id="fact_1",
            claim="Model X costs $20 per month for standard users",
            claim_type="price",
            numeric_value=20.0,
            currency="USD",
            status="strongly_supported",
            confidence=95.0,
            time_sensitive=True,
            attribution_required=False,
            writer_policy="safe_to_state_as_fact",
        ),
        VerifiedFactHandoff(
            claim_id="fact_2",
            claim="Model X supports 4K video rendering output",
            claim_type="capability",
            status="supported",
            confidence=90.0,
            time_sensitive=False,
            attribution_required=False,
            writer_policy="safe_to_state_as_fact",
        ),
    ]
    return FinalResearchPackage(
        research_project_id="proj_1",
        opportunity_id="opp_1",
        topic="Model X Video Generator",
        research_objective="Evaluate capabilities and pricing",
        executive_summary="Summary of Model X",
        verified_facts=facts,
        uncertain_claims=[],
        contradictions=[],
        timeline=[],
        entities=[],
        primary_sources=[{"id": "src_1", "tier": 1, "url": "https://official.modelx.com"}],
        supporting_sources=[],
        research_questions=ResearchQuestionsSummary(
            answered=["What is Model X?", "How much does Model X cost?"],
            partially_answered=[],
            unanswered=[],
        ),
        content_gaps=[],
        important_numbers=[{"value": 20.0, "currency": "USD", "claim": "Model X costs $20/month"}],
        important_dates=[],
        limitations=["Requires high bandwidth for 4K rendering"],
        risk_flags=[],
        research_quality_score=92.0,
        research_confidence_score=94.0,
        source_quality_score=95.0,
        critical_claim_coverage_score=100.0,
        instructions_for_writer=WriterInstructions(
            safe_claim_ids=["fact_1", "fact_2"],
            attribution_required_claim_ids=[],
            do_not_state_as_fact_claim_ids=[],
            time_sensitive_claim_ids=["fact_1"],
        ),
        citation_map={"fact_1": ["src_1"], "fact_2": ["src_1"]},
    )


def test_strategy_pricing_intent(mock_research_package: FinalResearchPackage):
    strategy = ContentStrategist.develop_strategy(
        research_pkg=mock_research_package,
        primary_keyword="model x pricing",
        search_intent="commercial_investigation",
        target_audience=["video creators"],
    )
    assert strategy.recommended_content_type == ContentType.PRICING.value
    assert "pricing" in strategy.reader_problem.lower()
    assert strategy.target_length_min >= 900
    assert "Direct primary-source documentation" in strategy.differentiation_strategy


def test_strategy_tutorial_intent(mock_research_package: FinalResearchPackage):
    strategy = ContentStrategist.develop_strategy(
        research_pkg=mock_research_package,
        primary_keyword="how to use model x",
        search_intent="tutorial",
        target_audience=["beginners"],
    )
    assert strategy.recommended_content_type == ContentType.TUTORIAL.value
    assert "step-by-step" in strategy.reader_problem.lower()


def test_strategy_override(mock_research_package: FinalResearchPackage):
    strategy = ContentStrategist.develop_strategy(
        research_pkg=mock_research_package,
        primary_keyword="model x",
        search_intent="informational",
        content_type_override="comparison",
        tone_override="analytical",
    )
    assert strategy.recommended_content_type == "comparison"
    assert strategy.tone == "analytical"
