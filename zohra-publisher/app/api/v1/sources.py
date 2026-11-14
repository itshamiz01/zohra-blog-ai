"""Zohra Part 2 — Source Registry API endpoints.

GET    /api/v1/sources
POST   /api/v1/sources
GET    /api/v1/sources/{id}
PATCH  /api/v1/sources/{id}
POST   /api/v1/sources/{id}/enable
POST   /api/v1/sources/{id}/disable
POST   /api/v1/sources/{id}/test
"""

from __future__ import annotations

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_token
from app.db.models.sources import Source
from app.db.session import get_db
from app.discovery.adapters.rss import RSSAdapter
from app.schemas.api import ApiResponse
from app.schemas.discovery import (
    SourceCreate,
    SourceResponse,
    SourceTestResult,
    SourceUpdate,
)
from app.services.audit import AuditService

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get("", response_model=ApiResponse[list[SourceResponse]])
async def list_sources(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
    is_enabled: bool | None = None,
    tier: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[list[SourceResponse]]:
    """List configured discovery sources with optional filtering."""
    query = select(Source).order_by(Source.priority.desc(), Source.created_at.desc())
    if category:
        query = query.where(Source.category == category)
    if is_enabled is not None:
        query = query.where(Source.is_enabled == is_enabled)
    if tier is not None:
        query = query.where(Source.tier == tier)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    sources = list(result.scalars().all())

    return ApiResponse(
        success=True,
        data=[SourceResponse.model_validate(s) for s in sources],
    )


@router.post("", response_model=ApiResponse[SourceResponse], status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: SourceCreate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SourceResponse]:
    """Register a new discovery source."""
    # Check domain/url collision
    existing = await db.execute(
        select(Source).where((Source.base_url == payload.base_url) | (Source.name == payload.name))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source with this name or base_url already exists",
        )

    source = Source(**payload.model_dump())
    db.add(source)
    await db.flush()

    await AuditService.log_action(
        db=db,
        action="SOURCE_CREATED",
        entity_type="source",
        entity_id=str(source.id),
        actor_id=_token.get("sub"),
        changes=payload.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(source)

    return ApiResponse(
        success=True,
        data=SourceResponse.model_validate(source),
        message="Source created successfully",
    )


@router.get("/{source_id}", response_model=ApiResponse[SourceResponse])
async def get_source(
    source_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SourceResponse]:
    """Get source details by ID."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return ApiResponse(success=True, data=SourceResponse.model_validate(source))


@router.patch("/{source_id}", response_model=ApiResponse[SourceResponse])
async def update_source(
    source_id: UUID,
    payload: SourceUpdate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SourceResponse]:
    """Update source configuration."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return ApiResponse(success=True, data=SourceResponse.model_validate(source))

    for field, val in update_data.items():
        setattr(source, field, val)

    await AuditService.log_action(
        db=db,
        action="SOURCE_UPDATED",
        entity_type="source",
        entity_id=str(source.id),
        actor_id=_token.get("sub"),
        changes=update_data,
    )
    await db.commit()
    await db.refresh(source)

    return ApiResponse(
        success=True,
        data=SourceResponse.model_validate(source),
        message="Source updated successfully",
    )


@router.post("/{source_id}/enable", response_model=ApiResponse[SourceResponse])
async def enable_source(
    source_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SourceResponse]:
    """Enable a discovery source."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    source.is_enabled = True
    await AuditService.log_action(
        db=db,
        action="SOURCE_ENABLED",
        entity_type="source",
        entity_id=str(source.id),
        actor_id=_token.get("sub"),
    )
    await db.commit()
    await db.refresh(source)
    return ApiResponse(success=True, data=SourceResponse.model_validate(source))


@router.post("/{source_id}/disable", response_model=ApiResponse[SourceResponse])
async def disable_source(
    source_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SourceResponse]:
    """Disable a discovery source."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    source.is_enabled = False
    await AuditService.log_action(
        db=db,
        action="SOURCE_DISABLED",
        entity_type="source",
        entity_id=str(source.id),
        actor_id=_token.get("sub"),
    )
    await db.commit()
    await db.refresh(source)
    return ApiResponse(success=True, data=SourceResponse.model_validate(source))


@router.post("/{source_id}/test", response_model=ApiResponse[SourceTestResult])
async def test_source(
    source_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SourceTestResult]:
    """Test fetching from a source live and measure latency/parsing."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    adapter = RSSAdapter()
    start = time.perf_counter()
    fetch_res = await adapter.fetch(source)
    latency = (time.perf_counter() - start) * 1000

    test_res = SourceTestResult(
        source_id=source.id,
        success=fetch_res.success,
        status_code=fetch_res.status_code,
        items_found=len(fetch_res.items),
        response_time_ms=round(latency, 2),
        error=fetch_res.error_message,
    )
    return ApiResponse(success=fetch_res.success, data=test_res)
