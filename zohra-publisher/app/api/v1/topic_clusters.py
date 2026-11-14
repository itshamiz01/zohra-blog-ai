"""
Zohra Part 3 — Topic Clusters API endpoints.

GET /api/v1/topic-clusters
GET /api/v1/topic-clusters/{id}
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_token
from app.db.models.topic_clusters import TopicCluster
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.opportunity import TopicClusterResponse

router = APIRouter(prefix="/topic-clusters", tags=["Topic Clusters"])


@router.get("", response_model=ApiResponse[list[TopicClusterResponse]])
async def list_topic_clusters(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[list[TopicClusterResponse]]:
    """List structural topic clusters."""
    query = select(TopicCluster).order_by(desc(TopicCluster.aggregate_opportunity_score))
    if site_id:
        query = query.where(TopicCluster.site_id == site_id)
    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    clusters = list(res.scalars().all())
    return ApiResponse(data=[TopicClusterResponse.model_validate(c) for c in clusters])


@router.get("/{cluster_id}", response_model=ApiResponse[TopicClusterResponse])
async def get_topic_cluster_detail(
    cluster_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[TopicClusterResponse]:
    """Retrieve detailed topic cluster information."""
    cluster = await db.get(TopicCluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic cluster not found")
    return ApiResponse(data=TopicClusterResponse.model_validate(cluster))
