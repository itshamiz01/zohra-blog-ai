"""
Zohra — Media & Featured Image REST API Endpoints.

Provides endpoints to:
- Retrieve article featured images with responsive variants.
- Trigger on-demand generation or regeneration.
- Apply manual editor overrides (alt-text, caption, approval).
- Execute background backfill for historical articles.
- Manage site-specific visual brand profiles.
- Securely serve local media assets with SSRF/path-traversal protection.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.rbac import require_role
from app.db.models.article_images import ArticleFeaturedMedia, ArticleImageBrandProfile
from app.db.models.operations import UserRole
from app.db.models.sites import Site
from app.db.session import get_db
from app.media.models import BrandProfile
from app.media.service import ArticleImageService
from app.schemas.api import ApiResponse

logger = get_logger("api.media")

router = APIRouter(prefix="/media", tags=["Media Engine"])


class GenerateImageRequest(BaseModel):
    site_id: uuid.UUID
    title: str
    topic: str
    category: str = "Technology"
    audience: str = "General"
    force_regenerate: bool = False


class OverrideImageRequest(BaseModel):
    alt_text: str | None = None
    caption: str | None = None
    is_approved: bool | None = None


class BrandProfileUpdateRequest(BaseModel):
    visual_style: str = "Modern clean editorial, authentic, balanced depth and natural light"
    preferred_composition: str = "Rule of thirds, clear focal subject, uncluttered background"
    preferred_mood: str = "Professional, intelligent, inviting, authentic"
    photography_preference: float = Field(ge=0.0, le=1.0, default=0.7)
    illustration_preference: float = Field(ge=0.0, le=1.0, default=0.3)
    logo_policy: str = "NO_LOGOS"
    text_overlay_policy: str = "NO_TEXT"
    aspect_ratio: str = "16:9"
    quality: str = "standard"


@router.get("/articles/{article_id}", response_model=ApiResponse[dict[str, Any]])
async def get_article_featured_image(
    article_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Retrieve active featured image for an article."""
    stmt = select(ArticleFeaturedMedia).where(
        ArticleFeaturedMedia.article_id == article_id,
        ArticleFeaturedMedia.is_active == True,
    ).order_by(ArticleFeaturedMedia.created_at.desc())
    res = await db.execute(stmt)
    media = res.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="No active featured media found for this article.")

    return ApiResponse(
        data={
            "id": str(media.id),
            "article_id": str(media.article_id),
            "site_id": str(media.site_id),
            "public_url": media.public_url,
            "alt_text": media.alt_text,
            "caption": media.caption,
            "mime_type": media.mime_type,
            "width": media.width,
            "height": media.height,
            "file_size_bytes": media.file_size_bytes,
            "content_hash": media.content_hash,
            "relevance_score": media.relevance_score,
            "responsive_variants": media.responsive_variants_json or [],
            "provenance": media.provenance_metadata or {},
            "is_approved": media.is_approved,
        }
    )


@router.post("/articles/{article_id}/generate", response_model=ApiResponse[dict[str, Any]])
async def generate_article_featured_image(
    article_id: uuid.UUID,
    payload: GenerateImageRequest,
    _user: Annotated[Any, Depends(require_role(UserRole.EDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Generate or regenerate a featured image for an article."""
    service = ArticleImageService(db)
    try:
        media = await service.generate_featured_image(
            article_id=article_id,
            site_id=payload.site_id,
            title=payload.title,
            topic=payload.topic,
            category=payload.category,
            audience=payload.audience,
            force_regenerate=payload.force_regenerate,
        )
        return ApiResponse(
            data={
                "id": str(media.id),
                "public_url": media.public_url,
                "alt_text": media.alt_text,
                "relevance_score": media.relevance_score,
                "width": media.width,
                "height": media.height,
                "generation_status": media.generation_status,
            }
        )
    except Exception as exc:
        logger.error(f"Image generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/articles/{article_id}/override", response_model=ApiResponse[dict[str, Any]])
async def override_article_featured_image(
    article_id: uuid.UUID,
    payload: OverrideImageRequest,
    _user: Annotated[Any, Depends(require_role(UserRole.EDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Manually update alt-text, caption, or approval status for an article's featured image."""
    stmt = select(ArticleFeaturedMedia).where(
        ArticleFeaturedMedia.article_id == article_id,
        ArticleFeaturedMedia.is_active == True,
    ).order_by(ArticleFeaturedMedia.created_at.desc())
    res = await db.execute(stmt)
    media = res.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="No active featured media found for this article.")

    if payload.alt_text is not None:
        media.alt_text = payload.alt_text.strip()
    if payload.caption is not None:
        media.caption = payload.caption.strip()
    if payload.is_approved is not None:
        media.is_approved = payload.is_approved

    await db.commit()
    await db.refresh(media)
    return ApiResponse(
        data={
            "id": str(media.id),
            "alt_text": media.alt_text,
            "caption": media.caption,
            "is_approved": media.is_approved,
        }
    )


@router.post("/backfill", response_model=ApiResponse[dict[str, Any]])
async def backfill_article_images(
    site_id: uuid.UUID,
    _user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    max_articles: int = Query(10, ge=1, le=50),
) -> ApiResponse[dict[str, Any]]:
    """Execute background backfill for historical articles without featured images."""
    service = ArticleImageService(db)
    results = await service.backfill_article_images(site_id=site_id, max_articles=max_articles)
    return ApiResponse(
        data={
            "site_id": str(site_id),
            "processed": len(results),
            "results": results,
        }
    )


@router.get("/brand-profiles/{site_id}", response_model=ApiResponse[dict[str, Any]])
async def get_brand_profile(
    site_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Retrieve brand image profile for a specific site."""
    service = ArticleImageService(db)
    bp = await service.get_or_create_brand_profile(site_id)
    return ApiResponse(data=bp.model_dump())


@router.post("/brand-profiles/{site_id}", response_model=ApiResponse[dict[str, Any]])
async def update_brand_profile(
    site_id: uuid.UUID,
    payload: BrandProfileUpdateRequest,
    _user: Annotated[Any, Depends(require_role(UserRole.EDITOR))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Create or update brand image profile for a site."""
    stmt = select(ArticleImageBrandProfile).where(ArticleImageBrandProfile.site_id == site_id)
    res = await db.execute(stmt)
    prof = res.scalar_one_or_none()

    if not prof:
        prof = ArticleImageBrandProfile(
            site_id=site_id,
            visual_style=payload.visual_style,
            preferred_composition=payload.preferred_composition,
            preferred_mood=payload.preferred_mood,
            photography_preference=payload.photography_preference,
            illustration_preference=payload.illustration_preference,
            logo_policy=payload.logo_policy,
            text_overlay_policy=payload.text_overlay_policy,
            aspect_ratio=payload.aspect_ratio,
            quality=payload.quality,
        )
        db.add(prof)
    else:
        prof.visual_style = payload.visual_style
        prof.preferred_composition = payload.preferred_composition
        prof.preferred_mood = payload.preferred_mood
        prof.photography_preference = payload.photography_preference
        prof.illustration_preference = payload.illustration_preference
        prof.logo_policy = payload.logo_policy
        prof.text_overlay_policy = payload.text_overlay_policy
        prof.aspect_ratio = payload.aspect_ratio
        prof.quality = payload.quality

    await db.commit()
    await db.refresh(prof)
    return ApiResponse(
        data={
            "site_id": str(prof.site_id),
            "visual_style": prof.visual_style,
            "aspect_ratio": prof.aspect_ratio,
            "quality": prof.quality,
        }
    )


@router.get("/storage/{subpath:path}")
async def serve_media_storage(subpath: str) -> Response:
    """
    Safely serves locally stored media assets with path-traversal prevention.
    """
    settings = get_settings()
    storage_root = Path(getattr(settings, "STORAGE_DIR", "./storage")).resolve()

    # Prevent path traversal
    target = (storage_root / subpath).resolve()
    if not str(target).startswith(str(storage_root)):
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Media file not found")

    content = target.read_bytes()
    mime = "image/webp" if target.suffix.lower() == ".webp" else "application/octet-stream"

    return Response(
        content=content,
        media_type=mime,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Disposition": f"inline; filename=\"{target.name}\"",
        },
    )
