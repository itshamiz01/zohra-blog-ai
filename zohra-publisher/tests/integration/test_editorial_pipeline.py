"""
Integration tests for EditorialPipeline end-to-end execution (Part 5).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.draft_projects import DraftProject, DraftProjectStatus
from app.db.models.research_packages import ResearchPackage
from app.db.models.research_projects import ResearchProject
from app.db.models.sites import Site
from app.editorial.pipeline import EditorialPipeline


@pytest.mark.asyncio
async def test_end_to_end_editorial_pipeline(db_session: AsyncSession):
    # 1. Setup Site & Opportunity
    site = Site(
        name="Tech Insights",
        domain="techinsights.example.com",
        default_language="en",
        primary_country="US",
        niche="technology",
    )
    db_session.add(site)
    await db_session.flush()

    opp = ContentOpportunity(
        site_id=site.id,
        canonical_topic="Model X Video Workflow",
        proposed_angle="Complete creator workflow guide",
        working_title="Model X Video Workflow: Complete Creator Guide",
        primary_keyword="model x video workflow",
        primary_intent="informational",
        content_type="explainer",
        opportunity_score=88.0,
        confidence_score=92.0,
    )
    db_session.add(opp)
    await db_session.flush()

    res_proj = ResearchProject(
        opportunity_id=opp.id,
        site_id=site.id,
        topic="Model X Video Workflow",
        research_objective="Verify features, pricing, and workflow",
        research_depth="STANDARD",
        status="completed",
        research_quality_score=92.0,
        research_confidence_score=94.0,
    )
    db_session.add(res_proj)
    await db_session.flush()

    # 2. Setup Part 4 ResearchPackage
    verified_facts = [
        {
            "claim_id": "c_pricing",
            "claim": "Model X standard plan costs $20 per month",
            "claim_type": "price",
            "numeric_value": 20.0,
            "currency": "USD",
            "status": "strongly_supported",
            "confidence": 96.0,
            "time_sensitive": True,
            "attribution_required": False,
            "writer_policy": "safe_to_state_as_fact",
            "evidence": [{"source_id": "src_1", "support": "supports"}],
        },
        {
            "claim_id": "c_feature",
            "claim": "Model X supports high-definition 4K video rendering",
            "claim_type": "capability",
            "status": "supported",
            "confidence": 91.0,
            "time_sensitive": False,
            "attribution_required": False,
            "writer_policy": "safe_to_state_as_fact",
            "evidence": [{"source_id": "src_1", "support": "supports"}],
        },
    ]

    res_pkg = ResearchPackage(
        research_project_id=res_proj.id,
        opportunity_id=opp.id,
        topic="Model X Video Workflow",
        research_objective="Verify features and pricing",
        executive_summary="Executive summary of research findings.",
        verified_facts_json=verified_facts,
        uncertain_claims_json=[],
        contradictions_json=[],
        timeline_json=[],
        entities_json=[],
        primary_sources_json=[{"id": "src_1", "tier": 1, "url": "https://official.modelx.com"}],
        supporting_sources_json=[],
        questions_answered_json=["How much does Model X cost?", "What resolution does it support?"],
        questions_unanswered_json=[],
        content_gaps_json=[],
        important_numbers_json=[{"value": 20.0, "currency": "USD", "claim": "Model X standard plan costs $20 per month"}],
        important_dates_json=[],
        limitations_json=["Rendering 4K requires a dedicated GPU"],
        risk_flags_json=[],
        research_quality_score=92.0,
        research_confidence_score=94.0,
    )
    db_session.add(res_pkg)
    await db_session.flush()

    # 3. Create DraftProject
    draft_proj = DraftProject(
        research_package_id=res_pkg.id,
        opportunity_id=opp.id,
        site_id=site.id,
        content_type="explainer",
        target_audience=["video creators"],
        primary_keyword="model x video workflow",
        primary_intent="informational",
        status=DraftProjectStatus.QUEUED.value,
        research_quality_score=res_pkg.research_quality_score,
    )
    db_session.add(draft_proj)
    await db_session.commit()

    # 4. Execute Editorial Pipeline
    pipeline = EditorialPipeline(db_session)
    editorial_pkg = await pipeline.execute_draft_project(
        draft_project_id=draft_proj.id,
        existing_site_content=[{"id": uuid.uuid4(), "title": "Video Editing Guide", "slug": "video-editing-guide"}],
    )

    # 5. Verify Results
    assert editorial_pkg is not None
    assert editorial_pkg.quality.draft_quality >= 75.0
    assert editorial_pkg.quality.grounding >= 85.0
    assert len(editorial_pkg.article.sections) >= 2
    assert "Model X" in editorial_pkg.headline
    assert editorial_pkg.slug_candidate is not None

    await db_session.refresh(draft_proj)
    assert draft_proj.status in (DraftProjectStatus.READY_FOR_PART6.value, DraftProjectStatus.NEEDS_HUMAN_REVIEW.value)
    assert draft_proj.draft_quality_score >= 75.0
