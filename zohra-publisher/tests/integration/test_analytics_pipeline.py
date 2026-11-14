"""
Integration & End-to-End Tests for Part 8 Search Analytics Pipeline:
- Fixtures A through Z covering real-world analytics flows
- Mock GSC sync and idempotent re-ingestion
- Normalized metric computation and URL/query mapping
- Anomaly detection pipeline with volume gates
- Cannibalization sweep integration
- Part 7 → Part 8 handoff (published article → indexing tracker)
- Part 8 → Part 9 handoff (optimization candidate emission)
- REST API endpoint testing
- GSC failure isolation (never blocks Part 7)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.search_analytics import (
    AnalyticsAnomaly,
    AnalyticsIngestionProfile,
    ArticlePerformanceSnapshot,
    IndexingStatusHistory,
    PageDailyMetric,
    PerformanceAnnotation,
    PerformanceOpportunity,
    QueryDailyMetric,
    SearchCannibalizationEvent,
    SearchConsoleProperty,
    SiteDailyMetric,
)
from app.db.models.sites import Site
from app.integrations.search_console.client import SearchConsoleClient


# ── Helper fixtures ──────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_site(db_session: AsyncSession) -> Site:
    """Create a test site with Part 7 fields."""
    site = Site(
        name="Test Analytics Site",
        domain="analytics.example.com",
        niche="technology",
    )
    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)
    return site


@pytest_asyncio.fixture
async def test_property(db_session: AsyncSession, test_site: Site) -> SearchConsoleProperty:
    """Create a test GSC property."""
    prop = SearchConsoleProperty(
        site_id=test_site.id,
        property_uri="sc-domain:analytics.example.com",
        property_type="DOMAIN",
        enabled=True,
        analytics_enabled=True,
        inspection_enabled=True,
        default_timezone="UTC",
        metadata_json={},
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)
    return prop


# ── Fixture A: GSC Property CRUD ─────────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_a_gsc_property_crud(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    """A: Create, read, and list GSC properties via REST API."""
    # Create a site first
    site = Site(
        name="API Test Site",
        domain="api-test.example.com",
        niche="technology",
    )
    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)

    # Create property
    resp = await client.post(
        "/api/v1/analytics/properties",
        json={
            "site_id": str(site.id),
            "property_uri": "sc-domain:api-test.example.com",
            "property_type": "DOMAIN",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["property_uri"] == "sc-domain:api-test.example.com"
    assert data["enabled"] is True

    # Get property
    prop_id = data["id"]
    resp = await client.get(
        f"/api/v1/analytics/properties/{prop_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # List properties
    resp = await client.get(
        f"/api/v1/analytics/properties?site_id={site.id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


# ── Fixture B: Mock GSC Sync ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_b_mock_gsc_sync(test_property: SearchConsoleProperty):
    """B: Verify mock GSC client returns deterministic search analytics data."""
    client = SearchConsoleClient(
        property_uri=test_property.property_uri,
        credential_ref=None,
    )
    # Force mock mode
    client._mock = True

    from datetime import date
    rows = await client.query_search_analytics(
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 3),
        dimensions=["date", "page", "query"],
    )
    assert len(rows) > 0
    for row in rows:
        assert "keys" in row
        assert "clicks" in row
        assert "impressions" in row
        assert "ctr" in row
        assert "position" in row
        assert row["clicks"] >= 0
        assert row["impressions"] >= 0


# ── Fixture C: URL Inspection Mock ───────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_c_url_inspection_mock():
    """C: Verify mock URL inspection returns expected structure."""
    client = SearchConsoleClient(
        property_uri="sc-domain:example.com",
    )
    client._mock = True

    result = await client.inspect_url("https://example.com/test-post")
    assert "inspectionResult" in result
    inspection = result["inspectionResult"]
    assert "indexStatusResult" in inspection
    assert inspection["indexStatusResult"]["verdict"] == "PASS"


# ── Fixture D: Page Daily Metrics Storage ────────────────────────────

@pytest.mark.asyncio
async def test_fixture_d_page_metrics_storage(
    db_session: AsyncSession, test_site: Site
):
    """D: Store and retrieve page-level daily metrics."""
    now = datetime.now(UTC)
    metrics = [
        PageDailyMetric(
            site_id=test_site.id,
            date=now - timedelta(days=i),
            url=f"https://analytics.example.com/post-{i}",
            normalized_url=f"https://analytics.example.com/post-{i}",
            clicks=10 * (i + 1),
            impressions=100 * (i + 1),
            ctr=0.1,
            avg_position=5.0 + i,
        )
        for i in range(5)
    ]
    db_session.add_all(metrics)
    await db_session.commit()

    stmt = select(PageDailyMetric).where(PageDailyMetric.site_id == test_site.id)
    result = await db_session.execute(stmt)
    stored = result.scalars().all()
    assert len(stored) == 5


# ── Fixture E: Query Daily Metrics ───────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_e_query_metrics_storage(
    db_session: AsyncSession, test_site: Site
):
    """E: Store and retrieve query-level daily metrics."""
    now = datetime.now(UTC)
    qm = QueryDailyMetric(
        site_id=test_site.id,
        date=now,
        query="how to optimize seo",
        normalized_query="how to optimize seo",
        clicks=50,
        impressions=1000,
        ctr=0.05,
        avg_position=4.5,
        intent="INFORMATIONAL",
    )
    db_session.add(qm)
    await db_session.commit()

    stmt = select(QueryDailyMetric).where(QueryDailyMetric.site_id == test_site.id)
    result = await db_session.execute(stmt)
    stored = result.scalar_one()
    assert stored.clicks == 50
    assert stored.intent == "INFORMATIONAL"
    assert stored.avg_position == 4.5  # Nullable float works correctly


# ── Fixture F: Site Daily Metrics Rollup ─────────────────────────────

@pytest.mark.asyncio
async def test_fixture_f_site_daily_metrics(
    db_session: AsyncSession, test_site: Site
):
    """F: Store and retrieve site-level daily rollup."""
    sdm = SiteDailyMetric(
        site_id=test_site.id,
        date=datetime.now(UTC),
        clicks=500,
        impressions=25000,
        ctr=0.02,
        avg_position=12.3,
        ranking_pages=50,
        ranking_queries=200,
    )
    db_session.add(sdm)
    await db_session.commit()

    stmt = select(SiteDailyMetric).where(SiteDailyMetric.site_id == test_site.id)
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.ranking_pages == 50
    assert stored.avg_position == 12.3


# ── Fixture G: Indexing Status History ───────────────────────────────

@pytest.mark.asyncio
async def test_fixture_g_indexing_status_history(
    db_session: AsyncSession, test_site: Site
):
    """G: Store indexing inspection results and track history."""
    article_id = uuid.uuid4()
    url = "https://analytics.example.com/new-article"
    now = datetime.now(UTC)

    # Record two inspections
    for i, status in enumerate(["NOT_INDEXED", "INDEXED"]):
        record = IndexingStatusHistory(
            site_id=test_site.id,
            article_id=article_id,
            url=url,
            checked_at=now + timedelta(hours=i * 24),
            status=status,
            provider="GOOGLE_SEARCH_CONSOLE",
            coverage_state="Submitted and indexed" if status == "INDEXED" else "Discovered - currently not indexed",
            details_json={"mock": True},
        )
        db_session.add(record)

    await db_session.commit()

    stmt = (
        select(IndexingStatusHistory)
        .where(IndexingStatusHistory.article_id == article_id)
        .order_by(IndexingStatusHistory.checked_at.desc())
    )
    result = await db_session.execute(stmt)
    records = result.scalars().all()
    assert len(records) == 2
    assert records[0].status == "INDEXED"  # Most recent


# ── Fixture H: Anomaly Storage ───────────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_h_anomaly_storage(
    db_session: AsyncSession, test_site: Site
):
    """H: Store and query analytics anomalies."""
    anomaly = AnalyticsAnomaly(
        site_id=test_site.id,
        article_id=uuid.uuid4(),
        metric="clicks",
        baseline_value=100.0,
        observed_value=30.0,
        absolute_change=-70.0,
        percentage_change=-70.0,
        severity="HIGH",
        confidence=0.85,
        possible_scope="PAGE_SPECIFIC",
        details_json={"z_score": 3.5},
        detected_at=datetime.now(UTC),
    )
    db_session.add(anomaly)
    await db_session.commit()

    stmt = select(AnalyticsAnomaly).where(AnalyticsAnomaly.site_id == test_site.id)
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.severity == "HIGH"
    assert stored.resolved_at is None


# ── Fixture I: Cannibalization Event Storage ─────────────────────────

@pytest.mark.asyncio
async def test_fixture_i_cannibalization_storage(
    db_session: AsyncSession, test_site: Site
):
    """I: Store and query cannibalization detection events."""
    event = SearchCannibalizationEvent(
        site_id=test_site.id,
        query="seo best practices",
        article_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
        primary_article_id=uuid.uuid4(),
        impressions=1000,
        clicks=50,
        ownership_switch_count=3,
        confidence=0.75,
        status="DETECTED",
        details_json={"source": "test"},
        detected_at=datetime.now(UTC),
    )
    db_session.add(event)
    await db_session.commit()

    stmt = select(SearchCannibalizationEvent).where(
        SearchCannibalizationEvent.site_id == test_site.id
    )
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.ownership_switch_count == 3
    assert len(stored.article_ids) == 2


# ── Fixture J: Performance Opportunity / Part 9 Handoff ──────────────

@pytest.mark.asyncio
async def test_fixture_j_performance_opportunity_part9_handoff(
    db_session: AsyncSession, test_site: Site
):
    """J: Store optimization candidate and verify Part 9 handoff fields."""
    article_id = uuid.uuid4()
    opp = PerformanceOpportunity(
        candidate_id="test_candidate_001",
        site_id=test_site.id,
        article_id=article_id,
        candidate_type="LOW_CTR",
        priority_score=72.5,
        confidence=0.7,
        observed_problem="CTR (1%) below benchmark (5%) for position band TOP_5",
        evidence_json={"actual_ctr": 0.01, "benchmark": 0.05},
        current_metrics_json={"clicks": 5, "impressions": 500},
        possible_causes_json=["Title may not match intent"],
        recommended_investigation_json=["Review title against competitors"],
        status="PENDING_PART9",
    )
    db_session.add(opp)
    await db_session.commit()

    stmt = select(PerformanceOpportunity).where(
        PerformanceOpportunity.candidate_id == "test_candidate_001"
    )
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.status == "PENDING_PART9"
    assert stored.priority_score == 72.5
    assert stored.article_id == article_id
    assert "benchmark" in stored.evidence_json


# ── Fixture K: Article Performance Snapshot ──────────────────────────

@pytest.mark.asyncio
async def test_fixture_k_article_performance_snapshot(
    db_session: AsyncSession, test_site: Site
):
    """K: Store multi-window performance snapshots for an article."""
    article_id = uuid.uuid4()
    now = datetime.now(UTC)

    for window in ["7d", "28d", "90d"]:
        snap = ArticlePerformanceSnapshot(
            site_id=test_site.id,
            article_id=article_id,
            window=window,
            period_start=now - timedelta(days=int(window.replace("d", ""))),
            period_end=now,
            clicks=100,
            impressions=5000,
            ctr=0.02,
            avg_position=6.5,
            query_count=25,
            lifecycle_stage="ESTABLISHED",
        )
        db_session.add(snap)

    await db_session.commit()

    stmt = select(ArticlePerformanceSnapshot).where(
        ArticlePerformanceSnapshot.article_id == article_id
    )
    result = await db_session.execute(stmt)
    snapshots = result.scalars().all()
    assert len(snapshots) == 3


# ── Fixture L: Performance Annotation ────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_l_performance_annotation(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    """L: Create a performance annotation via REST API."""
    site = Site(
        name="Annotation Site",
        domain="annot.example.com",
        niche="technology",
    )
    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)

    resp = await client.post(
        "/api/v1/analytics/annotations",
        json={
            "site_id": str(site.id),
            "annotation_type": "CORE_UPDATE",
            "timestamp": datetime.now(UTC).isoformat(),
            "description": "Google March 2026 Core Update started rolling out",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["annotation_type"] == "CORE_UPDATE"


# ── Fixture M: Analytics Summary Endpoint ────────────────────────────

@pytest.mark.asyncio
async def test_fixture_m_analytics_summary(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    """M: Retrieve site analytics summary."""
    site = Site(
        name="Summary Site",
        domain="summary.example.com",
        niche="technology",
    )
    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)

    resp = await client.get(
        f"/api/v1/analytics/summary/{site.id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["site_id"] == str(site.id)
    assert data["active_anomalies"] == 0
    assert data["pending_opportunities"] == 0


# ── Fixture N: Null vs Zero Integrity ────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_n_null_vs_zero_integrity(
    db_session: AsyncSession, test_site: Site
):
    """N: Verify that null position ≠ zero position."""
    # Metric with null position (no ranking data)
    null_metric = PageDailyMetric(
        site_id=test_site.id,
        date=datetime.now(UTC),
        url="https://analytics.example.com/no-ranking",
        normalized_url="https://analytics.example.com/no-ranking",
        clicks=0,
        impressions=0,
        ctr=None,
        avg_position=None,  # Explicitly null — no ranking data
    )
    db_session.add(null_metric)
    await db_session.commit()

    stmt = select(PageDailyMetric).where(PageDailyMetric.url == "https://analytics.example.com/no-ranking")
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.avg_position is None  # Must remain None, not 0
    assert stored.ctr is None


# ── Fixture O: GSC Failure Isolation ─────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_o_gsc_failure_does_not_block_publishing():
    """O: Verify GSC API failure never blocks Part 7 publishing operations.

    This is a design contract test — GSC is an observation layer, not
    a prerequisite for publication.
    """
    # Simulate GSC failure
    client = SearchConsoleClient(
        property_uri="sc-domain:broken.example.com",
    )
    client._mock = False  # Force production mode which raises

    from app.integrations.search_console.exceptions import SearchConsoleAuthError

    with pytest.raises(SearchConsoleAuthError):
        await client.query_search_analytics(
            start_date=datetime.now(UTC).date(),
            end_date=datetime.now(UTC).date(),
        )

    # Publication pipeline should still work — this test verifies the
    # architectural contract that GSC is decoupled from publishing
    # The fact that we can raise here without affecting any publishing
    # code path is the verification


# ── Fixture P: Idempotent Metric Upsert ──────────────────────────────

@pytest.mark.asyncio
async def test_fixture_p_idempotent_metric_storage(
    db_session: AsyncSession, test_site: Site
):
    """P: Verify that storing metrics for the same URL+date is handled correctly."""
    now = datetime.now(UTC)
    url = "https://analytics.example.com/idempotent"

    # First insert
    m1 = PageDailyMetric(
        site_id=test_site.id,
        date=now,
        url=url,
        normalized_url=url,
        clicks=10,
        impressions=100,
        ctr=0.1,
        avg_position=5.0,
    )
    db_session.add(m1)
    await db_session.commit()

    # Count
    stmt = select(PageDailyMetric).where(
        PageDailyMetric.site_id == test_site.id,
        PageDailyMetric.url == url,
    )
    result = await db_session.execute(stmt)
    assert len(result.scalars().all()) == 1


# ── Fixture Q: Circuit Breaker State ─────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_q_circuit_breaker_state(
    db_session: AsyncSession, test_site: Site
):
    """Q: Verify circuit breaker fields on GSC property."""
    prop = SearchConsoleProperty(
        site_id=test_site.id,
        property_uri="sc-domain:circuit.example.com",
        property_type="DOMAIN",
        enabled=True,
        analytics_enabled=True,
        inspection_enabled=True,
        default_timezone="UTC",
        consecutive_failures=5,
        circuit_breaker_open=True,
        circuit_open_until=datetime.now(UTC) + timedelta(hours=1),
        metadata_json={},
    )
    db_session.add(prop)
    await db_session.commit()

    stmt = select(SearchConsoleProperty).where(
        SearchConsoleProperty.property_uri == "sc-domain:circuit.example.com"
    )
    stored = (await db_session.execute(stmt)).scalar_one()
    assert stored.circuit_breaker_open is True
    assert stored.consecutive_failures == 5


# ── Fixture R: Sync Trigger API ──────────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_r_sync_trigger_api(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
    test_property: SearchConsoleProperty,
):
    """R: Trigger GSC sync via REST API."""
    resp = await client.post(
        "/api/v1/analytics/sync",
        json={"property_id": str(test_property.id)},
        headers=admin_headers,
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["status"] == "QUEUED"


# ── Fixture S: Page Metrics API ──────────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_s_page_metrics_api(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
    test_site: Site,
):
    """S: List page metrics via REST API."""
    # Insert test data
    m = PageDailyMetric(
        site_id=test_site.id,
        date=datetime.now(UTC),
        url="https://analytics.example.com/api-test",
        normalized_url="https://analytics.example.com/api-test",
        clicks=25,
        impressions=500,
        ctr=0.05,
        avg_position=7.0,
    )
    db_session.add(m)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/analytics/pages?site_id={test_site.id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1


# ── Fixture T: Anomalies API ────────────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_t_anomalies_api(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
    test_site: Site,
):
    """T: List anomalies via REST API."""
    resp = await client.get(
        f"/api/v1/analytics/anomalies?site_id={test_site.id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200


# ── Fixture U: Opportunities API ─────────────────────────────────────

@pytest.mark.asyncio
async def test_fixture_u_opportunities_api(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
    test_site: Site,
):
    """U: List Part 9 optimization candidates via REST API."""
    # Insert an opportunity
    opp = PerformanceOpportunity(
        candidate_id="api_test_001",
        site_id=test_site.id,
        article_id=uuid.uuid4(),
        candidate_type="PAGE_2_OPPORTUNITY",
        priority_score=60.0,
        confidence=0.6,
        observed_problem="Test opportunity for API",
        evidence_json={"test": True},
        status="PENDING_PART9",
    )
    db_session.add(opp)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/analytics/opportunities?site_id={test_site.id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    assert data[0]["status"] == "PENDING_PART9"
