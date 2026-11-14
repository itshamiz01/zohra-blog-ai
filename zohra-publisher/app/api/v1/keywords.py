"""
Zohra Part 3 — Keywords and Keyword Clusters API endpoints.

GET /api/v1/keywords
GET /api/v1/keywords/{id}
GET /api/v1/keyword-clusters
GET /api/v1/keyword-clusters/{id}
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import require_admin_token
from app.db.models.keyword_clusters import KeywordCluster, KeywordClusterMember
from app.db.models.keywords import Keyword
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.opportunity import (
    KeywordClusterResponse,
    KeywordResponse,
)

router = APIRouter(prefix="", tags=["Keywords & Clusters"])


@router.get("/keywords", response_model=ApiResponse[list[KeywordResponse]])
async def list_keywords(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    intent: str | None = None,
    language: str | None = None,
    country: str | None = None,
    min_demand: float | None = Query(default=None, ge=0.0, le=100.0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[list[KeywordResponse]]:
    """List discovered keywords with provenance-tracked metrics."""
    query = select(Keyword).order_by(desc(Keyword.search_demand_score))

    if intent:
        query = query.where(Keyword.intent == intent)
    if language:
        query = query.where(Keyword.language == language)
    if country:
        query = query.where(Keyword.country == country)
    if min_demand is not None:
        query = query.where(Keyword.search_demand_score >= min_demand)

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    keywords = list(res.scalars().all())
    return ApiResponse(data=[KeywordResponse.model_validate(k) for k in keywords])


@router.get("/keywords/{keyword_id}", response_model=ApiResponse[KeywordResponse])
async def get_keyword_detail(
    keyword_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[KeywordResponse]:
    """Retrieve detailed keyword metrics with explicit data provenance."""
    kw = await db.get(Keyword, keyword_id)
    if not kw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return ApiResponse(data=KeywordResponse.model_validate(kw))


@router.get("/keyword-clusters", response_model=ApiResponse[list[KeywordClusterResponse]])
async def list_keyword_clusters(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    intent: str | None = None,
    language: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[list[KeywordClusterResponse]]:
    """List grouped keyword clusters."""
    query = (
        select(KeywordCluster)
        .options(selectinload(KeywordCluster.members).selectinload(KeywordClusterMember.keyword))
        .order_by(desc(KeywordCluster.aggregate_demand_score))
    )

    if intent:
        query = query.where(KeywordCluster.primary_intent == intent)
    if language:
        query = query.where(KeywordCluster.language == language)

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    clusters = list(res.scalars().all())
    return ApiResponse(data=[KeywordClusterResponse.model_validate(c) for c in clusters])


@router.get("/keyword-clusters/{cluster_id}", response_model=ApiResponse[KeywordClusterResponse])
async def get_keyword_cluster_detail(
    cluster_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[KeywordClusterResponse]:
    """Retrieve keyword cluster detail and all its associated member keywords."""
    stmt = (
        select(KeywordCluster)
        .options(selectinload(KeywordCluster.members).selectinload(KeywordClusterMember.keyword))
        .where(KeywordCluster.id == cluster_id)
    )
    res = await db.execute(stmt)
    cluster = res.scalar_one_or_none()
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword cluster not found")
    return ApiResponse(data=KeywordClusterResponse.model_validate(cluster))
