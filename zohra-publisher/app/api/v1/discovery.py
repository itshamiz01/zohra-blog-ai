"""Zohra Part 2 — Discovery Pipeline Control & Analytics API.

POST /api/v1/discovery/run
POST /api/v1/discovery/pause
POST /api/v1/discovery/resume
GET  /api/v1/discovery/status
GET  /api/v1/discovery/stats
POST /api/v1/discovery/seed
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import CircuitBreakerState, EventStatus, SourceHealth
from app.core.security import require_admin_token
from app.db.models.events import Event
from app.db.models.source_documents import SourceDocument
from app.db.models.sources import Source
from app.db.models.system_settings import SystemSetting
from app.db.session import get_db
from app.discovery.pipeline import DiscoveryPipeline
from app.discovery.seeds import load_seed_sources
from app.schemas.api import ApiResponse
from app.schemas.discovery import (
    DiscoveryRunRequest,
    DiscoveryStatsResponse,
    DiscoveryStatusResponse,
)
from app.services.audit import AuditService
from app.services.cost import CostService

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.post("/run", response_model=ApiResponse[dict])
async def trigger_discovery_run(
    payload: DiscoveryRunRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Trigger a discovery pipeline cycle immediately."""
    settings = get_settings()
    if not settings.AUTONOMY_ENABLED and not payload.force:
        return ApiResponse(
            success=False,
            message="Autonomy engine is disabled globally. Pass force=true to override.",
            data={"status": "aborted"},
        )
    if not settings.ENABLE_DISCOVERY and not payload.force:
        return ApiResponse(
            success=False,
            message="Discovery engine is disabled in configuration. Pass force=true to override.",
            data={"status": "aborted"},
        )

    pipeline = DiscoveryPipeline(db=db)
    result = await pipeline.run_cycle(source_ids=payload.source_ids)

    await AuditService.log_action(
        db=db,
        action="DISCOVERY_RUN_TRIGGERED",
        entity_type="discovery_cycle",
        actor_id=_token.get("sub"),
        changes=result,
    )

    return ApiResponse(
        success=True,
        data=result,
        message=f"Discovery cycle processed {result.get('documents_processed', 0)} documents across {result.get('sources_polled', 0)} sources",
    )


@router.post("/pause", response_model=ApiResponse[dict])
async def pause_discovery(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Pause autonomous discovery operations."""
    stmt = select(SystemSetting).where(SystemSetting.key == "ENABLE_DISCOVERY")
    res = await db.execute(stmt)
    setting = res.scalar_one_or_none()
    if not setting:
        setting = SystemSetting(key="ENABLE_DISCOVERY", value="false", value_type="boolean")
        db.add(setting)
    else:
        setting.value = "false"

    await AuditService.log_action(
        db=db,
        action="DISCOVERY_PAUSED",
        entity_type="system_setting",
        actor_id=_token.get("sub"),
    )
    await db.commit()

    return ApiResponse(success=True, data={"discovery_enabled": False}, message="Discovery paused")


@router.post("/resume", response_model=ApiResponse[dict])
async def resume_discovery(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Resume autonomous discovery operations."""
    stmt = select(SystemSetting).where(SystemSetting.key == "ENABLE_DISCOVERY")
    res = await db.execute(stmt)
    setting = res.scalar_one_or_none()
    if not setting:
        setting = SystemSetting(key="ENABLE_DISCOVERY", value="true", value_type="boolean")
        db.add(setting)
    else:
        setting.value = "true"

    await AuditService.log_action(
        db=db,
        action="DISCOVERY_RESUMED",
        entity_type="system_setting",
        actor_id=_token.get("sub"),
    )
    await db.commit()

    return ApiResponse(success=True, data={"discovery_enabled": True}, message="Discovery resumed")


@router.get("/status", response_model=ApiResponse[DiscoveryStatusResponse])
async def discovery_status(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[DiscoveryStatusResponse]:
    """Get high-level status of the discovery engine and sources."""
    settings = get_settings()

    active_sources = (
        await db.scalar(select(func.count()).select_from(Source).where(Source.is_enabled.is_(True)))
        or 0
    )
    paused_sources = (
        await db.scalar(
            select(func.count()).select_from(Source).where(Source.is_enabled.is_(False))
        )
        or 0
    )
    circuit_open_sources = (
        await db.scalar(
            select(func.count())
            .select_from(Source)
            .where(Source.circuit_breaker_state == CircuitBreakerState.OPEN.value)
        )
        or 0
    )

    return ApiResponse(
        success=True,
        data=DiscoveryStatusResponse(
            autonomy_enabled=settings.AUTONOMY_ENABLED,
            discovery_enabled=settings.ENABLE_DISCOVERY,
            maintenance_mode=settings.MAINTENANCE_MODE,
            active_sources=active_sources,
            paused_sources=paused_sources,
            circuit_open_sources=circuit_open_sources,
            pending_tasks=0,
        ),
    )


@router.get("/stats", response_model=ApiResponse[DiscoveryStatsResponse])
async def discovery_stats(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[DiscoveryStatsResponse]:
    """Retrieve operational discovery metrics and today's aggregation."""
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    # Source counts
    sources_total = await db.scalar(select(func.count()).select_from(Source)) or 0
    sources_healthy = (
        await db.scalar(
            select(func.count())
            .select_from(Source)
            .where(Source.health_status == SourceHealth.HEALTHY)
        )
        or 0
    )
    sources_failing = (
        await db.scalar(
            select(func.count())
            .select_from(Source)
            .where(Source.health_status == SourceHealth.FAILING)
        )
        or 0
    )

    # Documents today
    docs_today = (
        await db.scalar(
            select(func.count())
            .select_from(SourceDocument)
            .where(SourceDocument.discovered_at >= today_start)
        )
        or 0
    )
    exact_dups = (
        await db.scalar(
            select(func.count())
            .select_from(SourceDocument)
            .where(
                SourceDocument.discovered_at >= today_start,
                SourceDocument.is_exact_duplicate.is_(True),
            )
        )
        or 0
    )
    near_dups = (
        await db.scalar(
            select(func.count())
            .select_from(SourceDocument)
            .where(
                SourceDocument.discovered_at >= today_start,
                SourceDocument.is_near_duplicate.is_(True),
            )
        )
        or 0
    )

    # Events breakdown
    active_events = (
        await db.scalar(
            select(func.count())
            .select_from(Event)
            .where(
                Event.status.in_(
                    [EventStatus.ACTIVE, EventStatus.ACCELERATING, EventStatus.EMERGING]
                )
            )
        )
        or 0
    )
    trending_events = (
        await db.scalar(select(func.count()).select_from(Event).where(Event.trend_score >= 70.0))
        or 0
    )
    emerging_events = (
        await db.scalar(
            select(func.count()).select_from(Event).where(Event.status == EventStatus.EMERGING)
        )
        or 0
    )
    qualified_events = (
        await db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.is_qualified_for_opportunity.is_(True))
        )
        or 0
    )

    # Categories breakdown
    cat_query = (
        select(Event.primary_category, func.count())
        .group_by(Event.primary_category)
        .where(Event.status.notin_([EventStatus.REJECTED, EventStatus.ARCHIVED]))
    )
    cat_res = await db.execute(cat_query)
    categories_breakdown = {row[0]: row[1] for row in cat_res.all()}

    # Language breakdown
    lang_query = (
        select(Event.language, func.count())
        .group_by(Event.language)
        .where(Event.status.notin_([EventStatus.REJECTED, EventStatus.ARCHIVED]))
    )
    lang_res = await db.execute(lang_query)
    languages_breakdown = {row[0]: row[1] for row in lang_res.all()}

    # Today's cost
    today_spend = await CostService.get_daily_spend(db=db)

    return ApiResponse(
        success=True,
        data=DiscoveryStatsResponse(
            sources_total=sources_total,
            sources_healthy=sources_healthy,
            sources_failing=sources_failing,
            documents_discovered_today=docs_today,
            exact_duplicates_blocked_today=exact_dups,
            near_duplicates_flagged_today=near_dups,
            active_events_count=active_events,
            trending_events_count=trending_events,
            emerging_events_count=emerging_events,
            qualified_opportunities_count=qualified_events,
            categories_breakdown=categories_breakdown,
            languages_breakdown=languages_breakdown,
            discovery_spend_usd_today=round(today_spend, 4),
        ),
    )


@router.post("/seed", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def seed_sources_endpoint(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Seed the source registry with curated high-quality default sources."""
    added = await load_seed_sources(db)
    await AuditService.log_action(
        db=db,
        action="SOURCES_SEEDED",
        entity_type="source_registry",
        actor_id=_token.get("sub"),
        changes={"sources_added": added},
    )
    return ApiResponse(
        success=True,
        data={"sources_added": added},
        message=f"Successfully loaded {added} seed sources into registry",
    )
