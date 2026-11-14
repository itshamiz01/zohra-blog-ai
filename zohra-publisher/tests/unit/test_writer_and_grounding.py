"""
Unit tests for ReviewRestrictionGuard, SectionWriter, DraftAssembler, GroundingVerifier, and BrandVoiceEngine (Part 5).
"""

from __future__ import annotations

import pytest

from app.editorial.grounding.verifier import GroundingVerifier
from app.editorial.voice.brand_voice import BrandVoiceEngine
from app.editorial.writer.review_guard import ReviewRestrictionGuard
from app.editorial.writer.section_writer import SectionWriter
from app.schemas.editorial import BrandVoiceProfileResponse, SectionBlueprint
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
            claim_id="c1",
            claim="Model X costs $20 per month for creators",
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
            claim_id="c2",
            claim="The company claims processing speeds are 2x faster than previous models",
            claim_type="capability",
            status="weakly_supported",
            confidence=65.0,
            time_sensitive=False,
            attribution_required=True,
            writer_policy="attribution_required",
        ),
    ]
    return FinalResearchPackage(
        research_project_id="proj_1",
        opportunity_id="opp_1",
        topic="Model X",
        research_objective="Objective",
        executive_summary="Summary",
        verified_facts=facts,
        uncertain_claims=[{"claim_id": "c_disputed", "claim": "Disputed feature"}],
        contradictions=[],
        timeline=[],
        entities=[],
        primary_sources=[{"id": "src_1", "tier": 1, "url": "https://modelx.ai"}],
        supporting_sources=[],
        research_questions=ResearchQuestionsSummary(answered=["Cost?"], partially_answered=[], unanswered=[]),
        content_gaps=[],
        important_numbers=[{"value": 20.0, "currency": "USD", "claim": "Model X costs $20 per month"}],
        important_dates=[],
        limitations=["Rendering 4K requires 16GB RAM"],
        risk_flags=[],
        research_quality_score=92.0,
        research_confidence_score=94.0,
        source_quality_score=95.0,
        critical_claim_coverage_score=100.0,
        instructions_for_writer=WriterInstructions(
            safe_claim_ids=["c1"],
            attribution_required_claim_ids=["c2"],
            do_not_state_as_fact_claim_ids=["c_disputed"],
            time_sensitive_claim_ids=["c1"],
        ),
        citation_map={"c1": ["src_1"], "c2": ["src_1"]},
    )


def test_review_restriction_guard():
    # Test unauthorized fake hands-on claims
    fake_text = "We tested Model X for three weeks in our lab, and our team ordered the Pro plan."
    assert ReviewRestrictionGuard.contains_fake_experience(fake_text)

    sanitized, modified = ReviewRestrictionGuard.sanitize_text(fake_text)
    assert modified
    assert "we tested" not in sanitized.lower()
    assert "our team ordered" not in sanitized.lower()
    assert "documented specifications" in sanitized


def test_section_writer_and_attribution(mock_research_package: FinalResearchPackage):
    bp = SectionBlueprint(
        section_id="sec_pricing",
        heading="Pricing and Plans",
        purpose="Explain cost",
        reader_question="How much does it cost?",
        target_claim_ids=["c1", "c2"],
        recommended_format="prose",
    )
    draft_sec = SectionWriter.write_section(
        section_bp=bp,
        allocated_facts=mock_research_package.verified_facts,
        research_pkg=mock_research_package,
    )
    assert "Model X costs $20" in draft_sec.content
    assert len(draft_sec.used_claim_ids) == 2
    assert len(draft_sec.citation_placements) == 2


def test_grounding_verifier(mock_research_package: FinalResearchPackage):
    content = "Model X costs $20 per month for creators. According to reported documentation, the company claims processing speeds are 2x faster."
    report = GroundingVerifier.verify_draft(content, mock_research_package)
    assert report.grounding_score >= 90.0
    assert report.attribution_compliant
    assert len(report.prohibited_claims_found) == 0


def test_brand_voice_factual_invariance():
    # Style transformation that preserves numbers
    text = "We utilize Model X. The subscription costs $20 and commenced in October 2026."
    profile = BrandVoiceProfileResponse(
        id=pytest.importorskip("uuid").uuid4(),
        site_id=pytest.importorskip("uuid").uuid4(),
        name="Tech Casual",
        tone="casual",
        formality="casual",
        sentence_style="clear",
        vocabulary_level="simple",
        preferred_patterns=[],
        avoid_patterns=[],
        humor_level="none",
        technical_depth="moderate",
        directness="high",
    )
    transformed, applied = BrandVoiceEngine.apply_voice(text, profile)
    assert applied
    assert "$20" in transformed
    assert "October 2026" in transformed
    assert "use Model X" in transformed  # utilize -> use
