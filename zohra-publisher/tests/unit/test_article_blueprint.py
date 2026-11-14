"""
Unit tests for ArticleBlueprintBuilder and ClaimAllocator (Part 5).
"""

from __future__ import annotations

import pytest

from app.editorial.blueprint.builder import ArticleBlueprintBuilder
from app.editorial.claims.allocator import ClaimAllocator
from app.editorial.strategy.strategist import ContentStrategist
from app.schemas.research import (
    FinalResearchPackage,
    ResearchQuestionsSummary,
    VerifiedFactHandoff,
    WriterInstructions,
)


@pytest.fixture
def sample_research_package() -> FinalResearchPackage:
    facts = [
        VerifiedFactHandoff(
            claim_id="fact_pricing",
            claim="Model X costs $20/month",
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
            claim_id="fact_feature",
            claim="Model X supports 4K resolution output",
            claim_type="capability",
            status="supported",
            confidence=90.0,
            time_sensitive=False,
            attribution_required=False,
            writer_policy="safe_to_state_as_fact",
        ),
        VerifiedFactHandoff(
            claim_id="fact_company_claim",
            claim="Model X renders 2x faster than previous models",
            claim_type="capability",
            status="weakly_supported",
            confidence=60.0,
            time_sensitive=False,
            attribution_required=True,
            writer_policy="attribution_required",
        ),
    ]
    return FinalResearchPackage(
        research_project_id="proj_1",
        opportunity_id="opp_1",
        topic="Model X Video Engine",
        research_objective="Capabilities and Pricing",
        executive_summary="Executive summary",
        verified_facts=facts,
        uncertain_claims=[{"claim_id": "disputed_1", "claim": "Model X has 100M users"}],
        contradictions=[],
        timeline=[],
        entities=[],
        primary_sources=[{"id": "src_1", "tier": 1, "url": "https://modelx.com"}],
        supporting_sources=[],
        research_questions=ResearchQuestionsSummary(
            answered=["How much does Model X cost?", "What resolution is supported?"],
            partially_answered=[],
            unanswered=[],
        ),
        content_gaps=[],
        important_numbers=[{"value": 20.0, "currency": "USD", "claim": "Model X costs $20/month"}],
        important_dates=[],
        limitations=["Requires 16GB RAM for local preview"],
        risk_flags=[],
        research_quality_score=90.0,
        research_confidence_score=92.0,
        source_quality_score=94.0,
        critical_claim_coverage_score=100.0,
        instructions_for_writer=WriterInstructions(
            safe_claim_ids=["fact_pricing", "fact_feature"],
            attribution_required_claim_ids=["fact_company_claim"],
            do_not_state_as_fact_claim_ids=["disputed_1"],
            time_sensitive_claim_ids=["fact_pricing"],
        ),
        citation_map={"fact_pricing": ["src_1"], "fact_feature": ["src_1"]},
    )


def test_blueprint_builder(sample_research_package: FinalResearchPackage):
    strategy = ContentStrategist.develop_strategy(
        research_pkg=sample_research_package,
        primary_keyword="model x pricing",
        search_intent="commercial_investigation",
    )
    blueprint = ArticleBlueprintBuilder.build_blueprint(
        research_pkg=sample_research_package,
        strategy=strategy,
        primary_keyword="model x pricing",
        secondary_keywords=["model x plans", "model x cost"],
    )

    assert len(blueprint.sections) >= 3
    assert blueprint.article_promise is not None
    assert any(s.section_id == "sec_pricing" for s in blueprint.sections)
    assert any(s.section_id == "sec_capabilities" for s in blueprint.sections)
    assert blueprint.table_plan is not None
    assert len(blueprint.faq_plan) > 0


def test_claim_allocator_blocks_prohibited_claims(sample_research_package: FinalResearchPackage):
    strategy = ContentStrategist.develop_strategy(
        research_pkg=sample_research_package,
        primary_keyword="model x",
        search_intent="informational",
    )
    blueprint = ArticleBlueprintBuilder.build_blueprint(
        research_pkg=sample_research_package,
        strategy=strategy,
        primary_keyword="model x",
    )
    # Inject disputed claim into blueprint section manually to test defense
    blueprint.sections[0].target_claim_ids.append("disputed_1")

    res = ClaimAllocator.allocate_claims(sample_research_package, blueprint)
    # Verify disputed claim is NOT allocated
    for _sec_id, facts in res.allocated_claims.items():
        assert all(f.claim_id != "disputed_1" for f in facts)
    assert "disputed_1" in res.prohibited_claim_ids
