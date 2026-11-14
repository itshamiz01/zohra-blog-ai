"""
Integration tests for ResearchPipeline end-to-end flow with database persistence.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.db.models.claims import Claim
from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.research_packages import ResearchPackage
from app.db.models.research_projects import ResearchProject
from app.db.models.research_sources import ResearchSource
from app.db.models.sites import Site
from app.research.pipeline import ResearchPipeline
from app.schemas.opportunity import ContentOpportunityPackage
from app.schemas.research import ResearchDepth


@pytest.mark.asyncio
async def test_end_to_end_research_pipeline(db_session):
    # 1. Create prerequisite Site and ContentOpportunity in database
    site = Site(
        name="AI Video Creator Hub",
        domain="aivideocreator.io",
        niche="Artificial Intelligence Video Tools",
        default_language="en",
        primary_country="US",
        target_audiences=["video creators", "editors"],
    )
    db_session.add(site)
    await db_session.flush()

    opp = ContentOpportunity(
        event_id=uuid.uuid4(),
        site_id=site.id,
        canonical_topic="Model X Video AI Workflow",
        proposed_angle="Step-by-step tutorial on how to use Model X",
        working_title="Complete Guide to Model X Video AI",
        primary_keyword="how to use model x",
        primary_intent="tutorial",
        content_type="tutorial",
        target_audience=["video creators"],
        language="en",
        country="US",
        opportunity_score=87.0,
        confidence_score=85.0,
        recommended_action="CREATE",
    )
    db_session.add(opp)
    await db_session.flush()

    package = ContentOpportunityPackage(
        opportunity_id=str(opp.id),
        event_id=str(opp.event_id),
        site_id=str(site.id),
        topic="Model X Video AI Workflow",
        proposed_angle="Step-by-step tutorial on how to use Model X",
        working_title="Complete Guide to Model X Video AI",
        content_type="tutorial",
        target_audience=["video creators"],
        language="en",
        country="US",
        primary_keyword="how to use model x",
        secondary_keywords=["model x tutorial", "model x settings"],
        questions=["What does Model X cost?", "Does Model X export in 4K?"],
        entities=["Model X", "Runway Gen-2"],
        primary_intent="tutorial",
        trend_score=85.0,
        search_demand_score=82.0,
        competition_opportunity_score=75.0,
        site_relevance_score=95.0,
        topical_authority_score=70.0,
        freshness_score=90.0,
        evergreen_score=80.0,
        original_value_score=85.0,
        serp_gap_score=80.0,
        monetization_score=70.0,
        cannibalization_risk_score=15.0,
        opportunity_score=87.0,
        confidence_score=85.0,
        recommended_action="CREATE",
    )

    # 2. Provide multi-source research inputs
    sources_data = [
        {
            "url": "https://modelx.ai/docs/quickstart",
            "title": "Model X Official Documentation & Quickstart",
            "publisher": "Model X Official",
            "text": "Model X was released in October 2026. The platform supports 4K rendering and costs $20 per month. The step-by-step workflow features automated prompt ingestion, timeline sequencing, and key video generation features.",
            "source_tier": 1,
            "source_type": "official_documentation",
            "is_primary_source": True,
            "is_official_source": True,
            "published_at": datetime.now(UTC),
        },
        {
            "url": "https://creator-weekly.com/model-x-review",
            "title": "Model X First Impressions for Video Editors",
            "publisher": "Creator Weekly",
            "text": "Model X launched in October 2026 with a $20 per month plan. It supports 4K rendering.",
            "source_tier": 2,
            "source_type": "review",
            "is_primary_source": False,
            "is_official_source": False,
            "published_at": datetime.now(UTC),
        },
    ]

    pipeline = ResearchPipeline(db_session)
    final_pkg = await pipeline.run_research(
        package=package,
        research_depth=ResearchDepth.STANDARD,
        mock_source_data=sources_data,
    )

    # 3. Verify FinalResearchPackage handoff object
    assert final_pkg.research_project_id is not None
    assert final_pkg.opportunity_id == str(opp.id)
    assert final_pkg.topic == "Model X Video AI Workflow"
    assert len(final_pkg.verified_facts) >= 2
    assert len(final_pkg.instructions_for_writer.safe_claim_ids) >= 1
    assert final_pkg.research_quality_score >= 70.0
    assert final_pkg.research_confidence_score >= 70.0
    assert len(final_pkg.citation_map) >= 1

    # 4. Verify database persistence
    db_proj = (await db_session.execute(select(ResearchProject))).scalars().first()
    assert db_proj is not None
    assert db_proj.status == "completed"
    assert db_proj.source_count == 2
    assert db_proj.claim_count >= 2

    db_claims = (await db_session.execute(select(Claim))).scalars().all()
    assert len(db_claims) >= 2

    db_sources = (await db_session.execute(select(ResearchSource))).scalars().all()
    assert len(db_sources) == 2

    db_pkgs = (await db_session.execute(select(ResearchPackage))).scalars().all()
    assert len(db_pkgs) == 1
    assert db_pkgs[0].is_immutable is True
