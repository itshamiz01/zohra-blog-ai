"""
Zohra Part 3 — Site Profile, Topic Relevance & Content Index API endpoints.

GET    /api/v1/sites
POST   /api/v1/sites
GET    /api/v1/sites/{id}
PUT    /api/v1/sites/{id}
GET    /api/v1/sites/{id}/topics
POST   /api/v1/sites/{id}/topics
GET    /api/v1/sites/{id}/content
POST   /api/v1/sites/{id}/content
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_token
from app.db.models.site_content import SiteContent
from app.db.models.site_topics import SiteTopic
from app.db.models.sites import Site
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.opportunity import (
    SiteContentBase,
    SiteContentResponse,
    SiteCreate,
    SiteResponse,
    SiteTopicBase,
    SiteTopicResponse,
    SiteUpdate,
)

router = APIRouter(prefix="/sites", tags=["Sites & Content Profile"])


@router.get("", response_model=ApiResponse[list[SiteResponse]])
async def list_sites(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[SiteResponse]]:
    """List all configured website publications."""
    stmt = select(Site).order_by(Site.created_at.desc())
    res = await db.execute(stmt)
    sites = list(res.scalars().all())
    return ApiResponse(data=[SiteResponse.model_validate(s) for s in sites])


@router.post("", response_model=ApiResponse[SiteResponse], status_code=status.HTTP_201_CREATED)
async def create_site(
    payload: SiteCreate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SiteResponse]:
    """Register a new website publication profile."""
    existing = await db.execute(select(Site).where(Site.domain == payload.domain))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site domain already registered")

    site = Site(
        name=payload.name,
        domain=payload.domain,
        default_language=payload.default_language,
        primary_country=payload.primary_country,
        niche=payload.niche,
        description=payload.description,
        target_audiences=payload.target_audiences,
        enabled=payload.enabled,
        config_json=payload.config_json,
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return ApiResponse(data=SiteResponse.model_validate(site))


@router.get("/{site_id}", response_model=ApiResponse[SiteResponse])
async def get_site_detail(
    site_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SiteResponse]:
    """Retrieve site profile by ID."""
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return ApiResponse(data=SiteResponse.model_validate(site))


@router.put("/{site_id}", response_model=ApiResponse[SiteResponse])
async def update_site(
    site_id: UUID,
    payload: SiteUpdate,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SiteResponse]:
    """Update website profile niche, description, or targets."""
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    if payload.name is not None:
        site.name = payload.name
    if payload.niche is not None:
        site.niche = payload.niche
    if payload.description is not None:
        site.description = payload.description
    if payload.target_audiences is not None:
        site.target_audiences = payload.target_audiences
    if payload.enabled is not None:
        site.enabled = payload.enabled
    if payload.config_json is not None:
        site.config_json = payload.config_json

    await db.commit()
    await db.refresh(site)
    return ApiResponse(data=SiteResponse.model_validate(site))


@router.get("/{site_id}/topics", response_model=ApiResponse[list[SiteTopicResponse]])
async def list_site_topics(
    site_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[SiteTopicResponse]]:
    """List thematic relevance weights and topical authority proxies for a site."""
    stmt = select(SiteTopic).where(SiteTopic.site_id == site_id).order_by(SiteTopic.relevance_weight.desc())
    res = await db.execute(stmt)
    topics = list(res.scalars().all())
    return ApiResponse(data=[SiteTopicResponse.model_validate(t) for t in topics])


@router.post("/{site_id}/topics", response_model=ApiResponse[SiteTopicResponse], status_code=status.HTTP_201_CREATED)
async def add_site_topic(
    site_id: UUID,
    payload: SiteTopicBase,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SiteTopicResponse]:
    """Add a topic relevance weight and authority score for a site."""
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    topic = SiteTopic(
        site_id=site.id,
        topic_name=payload.topic_name,
        canonical_slug=payload.canonical_slug,
        relevance_weight=payload.relevance_weight,
        topical_authority_score=payload.topical_authority_score,
        historical_post_count=payload.historical_post_count,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return ApiResponse(data=SiteTopicResponse.model_validate(topic))


@router.get("/{site_id}/content", response_model=ApiResponse[list[SiteContentResponse]])
async def list_site_content(
    site_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[list[SiteContentResponse]]:
    """List indexed existing articles for cannibalization avoidance."""
    stmt = (
        select(SiteContent)
        .where(SiteContent.site_id == site_id)
        .order_by(SiteContent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    content = list(res.scalars().all())
    return ApiResponse(data=[SiteContentResponse.model_validate(c) for c in content])


@router.post("/{site_id}/content", response_model=ApiResponse[SiteContentResponse], status_code=status.HTTP_201_CREATED)
async def add_site_content(
    site_id: UUID,
    payload: SiteContentBase,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SiteContentResponse]:
    """Index an existing website article into the cannibalization prevention index."""
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    content = SiteContent(
        site_id=site.id,
        external_post_id=payload.external_post_id,
        url=payload.url,
        slug=payload.slug,
        title=payload.title,
        summary=payload.summary,
        primary_topic=payload.primary_topic,
        primary_keyword=payload.primary_keyword,
        secondary_keywords=payload.secondary_keywords,
        primary_intent=payload.primary_intent.value if hasattr(payload.primary_intent, "value") else payload.primary_intent,
        language=payload.language,
        country=payload.country,
        status=payload.status,
        performance_json=payload.performance_json,
        metadata_json=payload.metadata_json,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return ApiResponse(data=SiteContentResponse.model_validate(content))


@router.get("/{site_id}/health", response_model=ApiResponse[dict])
async def check_site_wordpress_health(
    site_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict]:
    """Test remote WordPress REST connection and permissions safely without exposing secrets."""
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    from app.integrations.wordpress.auth import CredentialVault
    from app.integrations.wordpress.client import WordPressClient

    creds = CredentialVault.get_credentials_for_site(
        site_id=str(site.id),
        credential_ref=site.credential_ref,
        base_url_override=site.wordpress_base_url,
        api_url_override=site.wordpress_api_url,
    )
    if not creds:
        return ApiResponse(data={"site_id": str(site.id), "healthy": False, "error": "No WordPress credentials configured"})

    try:
        client = WordPressClient(creds)
        health = await client.check_health()
        return ApiResponse(data={"site_id": str(site.id), **health})
    except Exception as exc:
        return ApiResponse(data={"site_id": str(site.id), "healthy": False, "error": str(exc)})

