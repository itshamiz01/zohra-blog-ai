"""Integration tests for OpportunityPipeline with database and mock SERP provider."""

import uuid

import pytest
from sqlalchemy import select

from app.db.models.content_gaps import ContentGap
from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.keyword_clusters import KeywordCluster
from app.db.models.keywords import Keyword
from app.db.models.serp import SERPSnapshot
from app.db.models.sites import Site
from app.discovery.handoff import QualifiedEventHandoff
from app.opportunity.pipeline import OpportunityPipeline


@pytest.mark.asyncio
async def test_end_to_end_opportunity_pipeline(db_session):
    pipeline = OpportunityPipeline()

    event_id = str(uuid.uuid4())
    handoff = QualifiedEventHandoff(
        event_id=event_id,
        canonical_title="Runway Releases Gen-3 AI Video Model for Creators",
        summary="A major generative artificial intelligence video model update with improved temporal consistency and camera controls.",
        category="Artificial Intelligence",
        event_type="launch",
        language="en",
        countries=["global", "us"],
        trend_score=85.0,
        velocity_score=15.0,
        confidence_score=90.0,
        entities=[
            {"name": "Runway", "type": "organization"},
            {"name": "Gen-3", "type": "product"},
        ],
        status="active",
    )

    # Run pipeline
    packages = await pipeline.process_event(session=db_session, event_handoff=handoff)

    # Verify qualified opportunities returned
    assert len(packages) >= 1
    pkg = packages[0]

    assert pkg.topic is not None
    assert pkg.primary_keyword is not None
    assert pkg.opportunity_score >= 65.0
    assert pkg.confidence_score >= 60.0
    assert pkg.recommended_action in ("CREATE", "UPDATE", "EXPAND")
    assert len(pkg.competitor_urls) >= 1

    # Verify database persistence
    sites = list((await db_session.execute(select(Site))).scalars().all())
    assert len(sites) >= 1

    keywords = list((await db_session.execute(select(Keyword))).scalars().all())
    assert len(keywords) > 0
    # STRICT ANTI-HALLUCINATION: verify search_volume and cpc are NULL
    for kw in keywords:
        assert kw.search_volume is None
        assert kw.cpc is None

    clusters = list((await db_session.execute(select(KeywordCluster))).scalars().all())
    assert len(clusters) > 0

    snaps = list((await db_session.execute(select(SERPSnapshot))).scalars().all())
    assert len(snaps) > 0

    opps = list((await db_session.execute(select(ContentOpportunity))).scalars().all())
    assert len(opps) > 0

    gaps = list((await db_session.execute(select(ContentGap))).scalars().all())
    assert len(gaps) > 0
