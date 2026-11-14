"""
Zohra — URL Normalizer & Page-to-Article Mapper (Part 8).

Provides deterministic URL normalization for matching Search Console URLs
to published article records:
- Strips trailing slashes, query parameters, fragments, and protocol variants
- Normalizes case for domain portion only
- Maps normalized URLs to article_id via published_articles registry
"""

from __future__ import annotations

import uuid
from urllib.parse import urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.published_articles import PublishedArticle

logger = get_logger("analytics.url_normalizer")


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent matching.

    Rules:
    - Lowercase scheme and host
    - Remove trailing slash from path (unless root)
    - Remove fragment
    - Remove query string
    - Normalize empty path to /
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
    if not path:
        path = "/"
    # Reconstruct without query, fragment
    return urlunparse((scheme, netloc, path, "", "", ""))


def extract_slug_from_url(url: str) -> str | None:
    """Extract the URL slug (last path segment) from a URL."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path or path == "/":
        return None
    segments = [s for s in path.split("/") if s]
    return segments[-1] if segments else None


async def map_url_to_article(
    db: AsyncSession,
    site_id: uuid.UUID,
    url: str,
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Resolve a URL to (article_id, published_article_id).

    Attempts exact match on `url` field, then slug-based fallback.
    Returns (None, None) if no match found.
    """
    normalized = normalize_url(url)

    # 1. Exact URL match
    stmt = (
        select(PublishedArticle)
        .where(
            PublishedArticle.site_id == site_id,
            PublishedArticle.url == url,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    pub_article = result.scalar_one_or_none()

    if pub_article:
        return pub_article.article_id, pub_article.id

    # 2. Normalized URL match
    stmt = (
        select(PublishedArticle)
        .where(PublishedArticle.site_id == site_id)
    )
    result = await db.execute(stmt)
    pub_articles = result.scalars().all()
    for pa in pub_articles:
        if normalize_url(pa.url) == normalized:
            return pa.article_id, pa.id

    # 3. Slug-based fallback
    slug = extract_slug_from_url(url)
    if slug:
        stmt = (
            select(PublishedArticle)
            .where(
                PublishedArticle.site_id == site_id,
                PublishedArticle.slug == slug,
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        pub_article = result.scalar_one_or_none()
        if pub_article:
            return pub_article.article_id, pub_article.id

    logger.debug("URL not mapped to article", url=url, site_id=str(site_id))
    return None, None
