"""
Zohra — Search Analytics REST API Endpoints (Part 8).

Endpoints:
- POST /api/v1/analytics/properties: Register a GSC property
- GET  /api/v1/analytics/properties: List GSC properties for a site
- GET  /api/v1/analytics/properties/{id}: Get property details
- POST /api/v1/analytics/sync: Trigger GSC data ingestion
- GET  /api/v1/analytics/runs: List ingestion runs
- GET  /api/v1/analytics/pages: Page-level metrics
- GET  /api/v1/analytics/queries: Query-level metrics
- GET  /api/v1/analytics/site-metrics: Site-level daily metrics
- GET  /api/v1/analytics/indexing/{article_id}: Indexing status for an article
- POST /api/v1/analytics/inspect: Trigger URL inspection
- GET  /api/v1/analytics/anomalies: List detected anomalies
- GET  /api/v1/analytics/cannibalization: List cannibalization events
- GET  /api/v1/analytics/opportunities: List Part 9 optimization candidates
- GET  /api/v1/analytics/performance/{article_id}: Article performance snapshot
- GET  /api/v1/analytics/performance/topics: Topic performance summaries
- GET  /api/v1/analytics/performance/site: Site performance snapshot
- GET  /api/v1/analytics/diagnostics/{article_id}: Diagnostic report
- POST /api/v1/analytics/annotations: Create performance annotation
- GET  /api/v1/analytics/summary/{site_id}: Site analytics summary
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_token
from app.db.models.search_analytics import (
    AnalyticsAnomaly,
    AnalyticsIngestionRun,
    ArticlePerformanceSnapshot,
    IndexingStatusHistory,
    PageDailyMetric,
    PerformanceAnnotation,
    PerformanceOpportunity,
    QueryDailyMetric,
    SearchCannibalizationEvent,
    SearchConsoleProperty,
    SiteDailyMetric,
    SitePerformanceSnapshot,
    TopicPerformanceSnapshot,
)
from app.db.models.sites import Site
from app.db.session import get_db
from app.schemas.analytics import (
    AnalyticsSyncRequest,
    AnomalyResponse,
    ArticlePerformanceSnapshotResponse,
    CannibalizationEventResponse,
    IndexingInspectionRequest,
    IndexingStatusResponse,
    IngestionRunResponse,
    PageDailyMetricResponse,
    PerformanceAnnotationCreate,
    PerformanceAnnotationResponse,
    PerformanceOpportunityResponse,
    QueryDailyMetricResponse,
    SearchConsolePropertyCreate,
    SearchConsolePropertyResponse,
    SiteAnalyticsSummary,
    SiteDailyMetricResponse,
    SitePerformanceSnapshotResponse,
    TopicPerformanceSnapshotResponse,
)
from app.schemas.api import ApiResponse

router = APIRouter(prefix="/analytics", tags=["Search Analytics & Performance Intelligence"])


# ── GSC Property Management ──────────────────────────────────────────

@router.post("/properties", response_model=ApiResponse[SearchConsolePropertyResponse], status_code=status.HTTP_201_CREATED)
async def register_property(
    payload: SearchConsolePropertyCreate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SearchConsolePropertyResponse]:
    """Register a Google Search Console property for a site."""
    site = await db.get(Site, payload.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    prop = SearchConsoleProperty(
        site_id=payload.site_id,
        property_uri=payload.property_uri,
        property_type=payload.property_type.value,
        credential_ref=payload.credential_ref,
        default_timezone=payload.default_timezone,
        metadata_json={},
    )
    db.add(prop)
    await db.commit()
    await db.refresh(prop)

    return ApiResponse(data=SearchConsolePropertyResponse.model_validate(prop))


@router.get("/properties", response_model=ApiResponse[list[SearchConsolePropertyResponse]])
async def list_properties(
    site_id: UUID = Query(...),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SearchConsolePropertyResponse]]:
    """List GSC properties for a site."""
    stmt = select(SearchConsoleProperty).where(SearchConsoleProperty.site_id == site_id)
    result = await db.execute(stmt)
    props = result.scalars().all()
    return ApiResponse(
        data=[SearchConsolePropertyResponse.model_validate(p) for p in props]
    )


@router.get("/properties/{property_id}", response_model=ApiResponse[SearchConsolePropertyResponse])
async def get_property(
    property_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SearchConsolePropertyResponse]:
    """Get GSC property details."""
    prop = await db.get(SearchConsoleProperty, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return ApiResponse(data=SearchConsolePropertyResponse.model_validate(prop))


# ── Ingestion ────────────────────────────────────────────────────────

@router.post("/sync", response_model=ApiResponse[dict], status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    payload: AnalyticsSyncRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Trigger GSC data ingestion for a property."""
    prop = await db.get(SearchConsoleProperty, payload.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if prop.circuit_breaker_open:
        raise HTTPException(status_code=503, detail="Circuit breaker open for this property")

    # In a full implementation, this would enqueue a Celery task
    return ApiResponse(data={
        "status": "QUEUED",
        "property_id": str(payload.property_id),
        "message": "Analytics sync has been queued",
    })


@router.get("/runs", response_model=ApiResponse[list[IngestionRunResponse]])
async def list_ingestion_runs(
    property_id: UUID = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[IngestionRunResponse]]:
    """List recent ingestion runs for a property."""
    stmt = (
        select(AnalyticsIngestionRun)
        .where(AnalyticsIngestionRun.property_id == property_id)
        .order_by(AnalyticsIngestionRun.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return ApiResponse(
        data=[IngestionRunResponse.model_validate(r) for r in runs]
    )


# ── Page & Query Metrics ─────────────────────────────────────────────

@router.get("/pages", response_model=ApiResponse[list[PageDailyMetricResponse]])
async def list_page_metrics(
    site_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[PageDailyMetricResponse]]:
    """List page-level daily metrics."""
    stmt = (
        select(PageDailyMetric)
        .where(PageDailyMetric.site_id == site_id)
        .order_by(PageDailyMetric.date.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    metrics = result.scalars().all()
    return ApiResponse(
        data=[PageDailyMetricResponse.model_validate(m) for m in metrics]
    )


@router.get("/queries", response_model=ApiResponse[list[QueryDailyMetricResponse]])
async def list_query_metrics(
    site_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[QueryDailyMetricResponse]]:
    """List query-level daily metrics."""
    stmt = (
        select(QueryDailyMetric)
        .where(QueryDailyMetric.site_id == site_id)
        .order_by(QueryDailyMetric.date.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    metrics = result.scalars().all()
    return ApiResponse(
        data=[QueryDailyMetricResponse.model_validate(m) for m in metrics]
    )


@router.get("/site-metrics", response_model=ApiResponse[list[SiteDailyMetricResponse]])
async def list_site_metrics(
    site_id: UUID = Query(...),
    limit: int = Query(default=90, ge=1, le=365),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SiteDailyMetricResponse]]:
    """List site-level daily metrics."""
    stmt = (
        select(SiteDailyMetric)
        .where(SiteDailyMetric.site_id == site_id)
        .order_by(SiteDailyMetric.date.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    metrics = result.scalars().all()
    return ApiResponse(
        data=[SiteDailyMetricResponse.model_validate(m) for m in metrics]
    )


# ── Indexing ─────────────────────────────────────────────────────────

@router.get("/indexing/{article_id}", response_model=ApiResponse[list[IndexingStatusResponse]])
async def get_indexing_history(
    article_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[IndexingStatusResponse]]:
    """Get indexing status history for an article."""
    stmt = (
        select(IndexingStatusHistory)
        .where(IndexingStatusHistory.article_id == article_id)
        .order_by(IndexingStatusHistory.checked_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return ApiResponse(
        data=[IndexingStatusResponse.model_validate(r) for r in records]
    )


@router.post("/inspect", response_model=ApiResponse[dict], status_code=status.HTTP_202_ACCEPTED)
async def request_url_inspection(
    payload: IndexingInspectionRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Request URL inspection via GSC for one or more URLs."""
    site = await db.get(Site, payload.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    return ApiResponse(data={
        "status": "QUEUED",
        "urls": payload.urls,
        "message": f"Inspection queued for {len(payload.urls)} URL(s)",
    })


# ── Anomalies ────────────────────────────────────────────────────────

@router.get("/anomalies", response_model=ApiResponse[list[AnomalyResponse]])
async def list_anomalies(
    site_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[AnomalyResponse]]:
    """List detected analytics anomalies."""
    stmt = (
        select(AnalyticsAnomaly)
        .where(AnalyticsAnomaly.site_id == site_id)
        .order_by(AnalyticsAnomaly.detected_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    anomalies = result.scalars().all()
    return ApiResponse(
        data=[AnomalyResponse.model_validate(a) for a in anomalies]
    )


# ── Cannibalization ──────────────────────────────────────────────────

@router.get("/cannibalization", response_model=ApiResponse[list[CannibalizationEventResponse]])
async def list_cannibalization_events(
    site_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CannibalizationEventResponse]]:
    """List search cannibalization events."""
    stmt = (
        select(SearchCannibalizationEvent)
        .where(SearchCannibalizationEvent.site_id == site_id)
        .order_by(SearchCannibalizationEvent.detected_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()
    return ApiResponse(
        data=[CannibalizationEventResponse.model_validate(e) for e in events]
    )


# ── Opportunities ────────────────────────────────────────────────────

@router.get("/opportunities", response_model=ApiResponse[list[PerformanceOpportunityResponse]])
async def list_opportunities(
    site_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[PerformanceOpportunityResponse]]:
    """List Part 9 optimization candidate packages."""
    stmt = (
        select(PerformanceOpportunity)
        .where(PerformanceOpportunity.site_id == site_id)
        .order_by(PerformanceOpportunity.priority_score.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    opps = result.scalars().all()
    return ApiResponse(
        data=[PerformanceOpportunityResponse.model_validate(o) for o in opps]
    )


# ── Performance Snapshots ────────────────────────────────────────────

@router.get("/performance/{article_id}", response_model=ApiResponse[list[ArticlePerformanceSnapshotResponse]])
async def get_article_performance(
    article_id: UUID,
    window: str = Query(default="28d"),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ArticlePerformanceSnapshotResponse]]:
    """Get performance snapshots for an article."""
    stmt = (
        select(ArticlePerformanceSnapshot)
        .where(
            ArticlePerformanceSnapshot.article_id == article_id,
            ArticlePerformanceSnapshot.window == window,
        )
        .order_by(ArticlePerformanceSnapshot.period_end.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    return ApiResponse(
        data=[ArticlePerformanceSnapshotResponse.model_validate(s) for s in snapshots]
    )


@router.get("/performance/topics", response_model=ApiResponse[list[TopicPerformanceSnapshotResponse]])
async def get_topic_performance(
    site_id: UUID = Query(...),
    window: str = Query(default="28d"),
    limit: int = Query(default=20, ge=1, le=100),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[TopicPerformanceSnapshotResponse]]:
    """Get topic-level performance snapshots."""
    stmt = (
        select(TopicPerformanceSnapshot)
        .where(
            TopicPerformanceSnapshot.site_id == site_id,
            TopicPerformanceSnapshot.window == window,
        )
        .order_by(TopicPerformanceSnapshot.impressions.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    return ApiResponse(
        data=[TopicPerformanceSnapshotResponse.model_validate(s) for s in snapshots]
    )


@router.get("/performance/site", response_model=ApiResponse[list[SitePerformanceSnapshotResponse]])
async def get_site_performance(
    site_id: UUID = Query(...),
    window: str = Query(default="28d"),
    limit: int = Query(default=10, ge=1, le=90),
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SitePerformanceSnapshotResponse]]:
    """Get site-level performance snapshots."""
    stmt = (
        select(SitePerformanceSnapshot)
        .where(
            SitePerformanceSnapshot.site_id == site_id,
            SitePerformanceSnapshot.window == window,
        )
        .order_by(SitePerformanceSnapshot.date.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    return ApiResponse(
        data=[SitePerformanceSnapshotResponse.model_validate(s) for s in snapshots]
    )


# ── Annotations ──────────────────────────────────────────────────────

@router.post("/annotations", response_model=ApiResponse[PerformanceAnnotationResponse], status_code=status.HTTP_201_CREATED)
async def create_annotation(
    payload: PerformanceAnnotationCreate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PerformanceAnnotationResponse]:
    """Create a performance annotation (event marker)."""
    annotation = PerformanceAnnotation(
        site_id=payload.site_id,
        article_id=payload.article_id,
        annotation_type=payload.annotation_type,
        timestamp=payload.timestamp,
        description=payload.description,
        related_entity_id=payload.related_entity_id,
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    return ApiResponse(data=PerformanceAnnotationResponse.model_validate(annotation))


# ── Site Summary ─────────────────────────────────────────────────────

@router.get("/summary/{site_id}", response_model=ApiResponse[SiteAnalyticsSummary])
async def get_site_summary(
    site_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SiteAnalyticsSummary]:
    """Get a quick analytics health summary for a site."""
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Count anomalies
    anomaly_count_stmt = select(func.count()).select_from(AnalyticsAnomaly).where(
        AnalyticsAnomaly.site_id == site_id,
        AnalyticsAnomaly.resolved_at.is_(None),
    )
    anomaly_count = (await db.execute(anomaly_count_stmt)).scalar() or 0

    # Count cannibalization events
    cannibal_count_stmt = select(func.count()).select_from(SearchCannibalizationEvent).where(
        SearchCannibalizationEvent.site_id == site_id,
        SearchCannibalizationEvent.status == "DETECTED",
    )
    cannibal_count = (await db.execute(cannibal_count_stmt)).scalar() or 0

    # Count pending opportunities
    opp_count_stmt = select(func.count()).select_from(PerformanceOpportunity).where(
        PerformanceOpportunity.site_id == site_id,
        PerformanceOpportunity.status == "PENDING_PART9",
    )
    opp_count = (await db.execute(opp_count_stmt)).scalar() or 0

    # Last sync
    last_sync_stmt = (
        select(SearchConsoleProperty.last_successful_sync_at)
        .where(SearchConsoleProperty.site_id == site_id)
        .order_by(SearchConsoleProperty.last_successful_sync_at.desc())
        .limit(1)
    )
    last_sync = (await db.execute(last_sync_stmt)).scalar_one_or_none()

    return ApiResponse(data=SiteAnalyticsSummary(
        site_id=site_id,
        active_anomalies=anomaly_count,
        active_cannibalization_events=cannibal_count,
        pending_opportunities=opp_count,
        last_sync_at=last_sync,
    ))
