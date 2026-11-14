"""
Zohra — Celery Background Tasks for Automatic Article Image Engine.

Provides asynchronous workers for:
- media.generate_article_image: Generates and attaches featured hero image for an article.
- media.backfill_article_images: Finds and processes published articles missing featured images.
- media.regenerate_article_image: Forces regeneration of an image with specific feedback.
"""

from __future__ import annotations

import asyncio
from typing import Any
import uuid

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models.draft_projects import DraftProject
from app.db.models.sites import Site
from app.db.session import async_session_factory
from app.media.service import ArticleImageService
from app.workers.celery_app import celery_app

logger = get_logger("workers.media_tasks")


@celery_app.task(
    name="media.generate_article_image",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
)
def generate_article_image_task(
    self: Any,
    article_id_str: str,
    site_id_str: str,
    title: str,
    topic: str,
    category: str = "Technology",
    publication_job_id_str: str | None = None,
    force_regenerate: bool = False,
) -> dict[str, Any]:
    """Background task to generate and attach a featured image for an article."""
    return asyncio.run(
        _async_generate_article_image(
            article_id_str=article_id_str,
            site_id_str=site_id_str,
            title=title,
            topic=topic,
            category=category,
            publication_job_id_str=publication_job_id_str,
            force_regenerate=force_regenerate,
        )
    )


async def _async_generate_article_image(
    article_id_str: str,
    site_id_str: str,
    title: str,
    topic: str,
    category: str = "Technology",
    publication_job_id_str: str | None = None,
    force_regenerate: bool = False,
) -> dict[str, Any]:
    async with async_session_factory() as session:
        service = ArticleImageService(session)
        try:
            media = await service.generate_featured_image(
                article_id=article_id_str,
                site_id=site_id_str,
                title=title,
                topic=topic,
                category=category,
                publication_job_id=publication_job_id_str,
                force_regenerate=force_regenerate,
            )
            return {
                "status": "SUCCESS",
                "media_id": str(media.id),
                "public_url": media.public_url,
                "alt_text": media.alt_text,
                "content_hash": media.content_hash,
            }
        except Exception as exc:
            logger.error(f"Failed to generate article image: {exc}")
            return {"status": "FAILED", "error": str(exc)}


@celery_app.task(
    name="media.backfill_article_images",
    bind=True,
)
def backfill_article_images_task(
    self: Any,
    site_id_str: str,
    max_articles: int = 10,
) -> dict[str, Any]:
    """Background worker to backfill images for articles missing media."""
    return asyncio.run(_async_backfill_article_images(site_id_str, max_articles))


async def _async_backfill_article_images(
    site_id_str: str,
    max_articles: int = 10,
) -> dict[str, Any]:
    async with async_session_factory() as session:
        service = ArticleImageService(session)
        results = await service.backfill_article_images(site_id_str, max_articles)
        return {
            "site_id": site_id_str,
            "processed": len(results),
            "results": results,
        }
