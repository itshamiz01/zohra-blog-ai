"""
Zohra — Final SEO Packager & Structured Data Schema Engine (Part 7).

Manages:
- SEO packaging: title immutability, meta description, clean hyphenated slugs, canonical URLs.
- Slug collision detection: resolves duplicate slugs with deterministic numerical increments.
- Robots directives and Open Graph / Twitter metadata.
- JSON-LD Schema generation: validates eligible structured data (Article, NewsArticle, BlogPosting, FAQPage, HowTo)
  matching only visible article content without fabricated schema values.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger
from app.schemas.publishing import SEOPackageData

logger = get_logger("publishing.seo.packager")


class SEOPackager:
    """Constructs final SEO metadata packages and structured data."""

    @classmethod
    def clean_slug(cls, title: str) -> str:
        """Generates a clean, short, lowercase, hyphenated slug."""
        text = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", text).strip("-")
        return slug[:80]

    @classmethod
    def resolve_slug_collision(cls, desired_slug: str, existing_slugs: set[str]) -> str:
        """Resolves collisions by appending -2, -3, etc."""
        if desired_slug not in existing_slugs:
            return desired_slug

        counter = 2
        while f"{desired_slug}-{counter}" in existing_slugs:
            counter += 1
        return f"{desired_slug}-{counter}"

    @classmethod
    def build_seo_package(
        cls,
        title: str,
        meta_description: str,
        base_url: str,
        primary_keyword: str | None = None,
        primary_topic: str | None = None,
        existing_slugs: set[str] | None = None,
        featured_image_url: str | None = None,
    ) -> SEOPackageData:
        """Constructs canonical URL, slug, meta tags, and Open Graph objects."""
        raw_slug = cls.clean_slug(title)
        slug = cls.resolve_slug_collision(raw_slug, existing_slugs or set())
        clean_base = base_url.rstrip("/")
        canonical_url = f"{clean_base}/{slug}/"

        meta_desc = meta_description.strip()
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:157] + "..."

        return SEOPackageData(
            title=title,
            meta_title=title[:60],
            meta_description=meta_desc,
            slug=slug,
            canonical_url=canonical_url,
            primary_topic=primary_topic,
            primary_keyword=primary_keyword,
            robots_directive="index,follow",
            open_graph_title=title,
            open_graph_description=meta_desc,
            open_graph_image_url=featured_image_url,
            twitter_title=title,
            twitter_description=meta_desc,
            twitter_image_url=featured_image_url,
        )


class SchemaEngine:
    """Builds valid JSON-LD structured data strictly reflecting visible article content."""

    @classmethod
    def generate_article_schema(
        cls,
        title: str,
        canonical_url: str,
        published_at_iso: str,
        author_name: str = "Editorial Team",
        publisher_name: str = "Zohra",
        featured_image_url: str | None = None,
        faqs: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Generates Article schema and optional FAQPage schema."""
        schema: dict[str, Any] = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Article",
                    "headline": title,
                    "mainEntityOfPage": canonical_url,
                    "datePublished": published_at_iso,
                    "dateModified": published_at_iso,
                    "author": {
                        "@type": "Person",
                        "name": author_name,
                    },
                    "publisher": {
                        "@type": "Organization",
                        "name": publisher_name,
                    },
                }
            ],
        }

        if featured_image_url:
            schema["@graph"][0]["image"] = [featured_image_url]

        # Add FAQ schema if visible FAQs exist
        if faqs:
            faq_entities = []
            for faq in faqs:
                q = faq.get("question")
                a = faq.get("answer")
                if q and a:
                    faq_entities.append(
                        {
                            "@type": "Question",
                            "name": q,
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": a,
                            },
                        }
                    )
            if faq_entities:
                schema["@graph"].append(
                    {
                        "@type": "FAQPage",
                        "mainEntity": faq_entities,
                    }
                )

        return schema
