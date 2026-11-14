"""
Unit tests for DraftQualityScorer, RevisionEngine, ResearchFollowupHandler, and MultilingualEngine (Part 5).
"""

from __future__ import annotations

import pytest

from app.editorial.multilingual.engine import MultilingualEngine
from app.editorial.quality.scorer import DraftQualityScorer
from app.editorial.research_loop.followup import ResearchFollowupHandler
from app.schemas.editorial import (
    ContentStrategyData,
    SectionBlueprint,
)
from app.schemas.research import (
    FinalResearchPackage,
    ResearchQuestionsSummary,
    VerifiedFactHandoff,
    WriterInstructions,
)


@pytest.fixture
def mock_pkg() -> FinalResearchPackage:
    facts = [
        VerifiedFactHandoff(
            claim_id="f1",
            claim="Model X costs $20/month",
            claim_type="price",
            numeric_value=20.0,
            currency="USD",
            status="strongly_supported",
            confidence=95.0,
            time_sensitive=True,
            attribution_required=False,
            writer_policy="safe_to_state_as_fact",
        )
    ]
    return FinalResearchPackage(
        research_project_id="proj_1",
        opportunity_id="opp_1",
        topic="Model X",
        research_objective="Review",
        executive_summary="Summary",
        verified_facts=facts,
        uncertain_claims=[],
        contradictions=[],
        timeline=[],
        entities=[],
        primary_sources=[{"id": "s1", "tier": 1, "url": "https://modelx.ai"}],
        supporting_sources=[],
        research_questions=ResearchQuestionsSummary(answered=["Cost?"], partially_answered=[], unanswered=[]),
        content_gaps=[],
        important_numbers=[{"value": 20.0, "currency": "USD", "claim": "Model X costs $20/month"}],
        important_dates=[],
        limitations=["Requires GPU"],
        risk_flags=[],
        research_quality_score=92.0,
        research_confidence_score=95.0,
        source_quality_score=95.0,
        critical_claim_coverage_score=100.0,
        instructions_for_writer=WriterInstructions(
            safe_claim_ids=["f1"],
            attribution_required_claim_ids=[],
            do_not_state_as_fact_claim_ids=[],
            time_sensitive_claim_ids=["f1"],
        ),
        citation_map={"f1": ["s1"]},
    )


def test_draft_quality_scorer(mock_pkg: FinalResearchPackage):
    content = "# Model X\n\nModel X costs $20/month.\n\n## Overview\n\nVerified information.\n\n## Pricing\n\nDetailed pricing.\n"
    scores = DraftQualityScorer.score_draft(
        content=content,
        title="Model X Overview",
        primary_keyword="model x",
        grounding_score=95.0,
        seo_content_score=85.0,
        research_pkg=mock_pkg,
    )
    assert scores.draft_quality >= 75.0
    assert scores.classification in ("PART_6_ELIGIBLE", "STRONG_DRAFT", "EXCEPTIONAL_DRAFT")


def test_research_followup_detection():
    # If strategy is pricing but research has 0 pricing facts
    pkg_no_pricing = FinalResearchPackage(
        research_project_id="p1",
        opportunity_id="o1",
        topic="Model X",
        research_objective="Obj",
        executive_summary="Sum",
        verified_facts=[],
        uncertain_claims=[],
        contradictions=[],
        timeline=[],
        entities=[],
        primary_sources=[],
        supporting_sources=[],
        research_questions=ResearchQuestionsSummary(answered=[], partially_answered=[], unanswered=[]),
        content_gaps=[],
        important_numbers=[],
        important_dates=[],
        limitations=[],
        risk_flags=[],
        research_quality_score=70.0,
        research_confidence_score=70.0,
        source_quality_score=70.0,
        critical_claim_coverage_score=50.0,
        instructions_for_writer=WriterInstructions(),
        citation_map={},
    )
    strat = ContentStrategyData(
        reader_problem="Check pricing",
        reader_goal="Pricing",
        search_intent="commercial",
        content_goal="Explain price",
        recommended_content_type="pricing",
        angle="Pricing",
        differentiation_strategy="Direct",
        information_gain_strategy="Gain",
        tone="professional",
        depth="standard",
        target_length_min=1000,
        target_length_max=1600,
    )
    missing = ResearchFollowupHandler.identify_missing_critical_facts(pkg_no_pricing, strat)
    assert len(missing) > 0
    assert missing[0]["priority"] == "critical"
    assert "pricing" in missing[0]["reason"].lower()


def test_multilingual_consistency(mock_pkg: FinalResearchPackage):
    sec_bp = SectionBlueprint(
        section_id="sec_pricing",
        heading="Pricing and Plans",
        purpose="Explain cost",
        reader_question="How much does it cost?",
        target_claim_ids=["f1"],
    )
    # Generate in Hindi
    hi_sec = MultilingualEngine.adapt_section(
        section_bp=sec_bp,
        allocated_facts=mock_pkg.verified_facts,
        language="hi",
        topic="Model X",
    )
    assert "$20" in hi_sec.content
    assert "Model X" in hi_sec.content

    # Verify numbers match English version
    en_content = "Model X costs $20/month."
    assert MultilingualEngine.verify_multilingual_consistency(en_content, hi_sec.content)
