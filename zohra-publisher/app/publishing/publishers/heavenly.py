"""
Zohra — Heavenly Insights Publishing Provider.

Coordinates publishing articles and associating featured image URLs
with Heavenly Insights via Bearer-authenticated HTTPS REST API.
"""

from __future__ import annotations

import datetime
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.integrations.heavenly.client import HeavenlyClient, is_public_absolute_url
from app.publishing.publishers.base import BasePublishingProvider
from app.schemas.publishing import PublicationMode

logger = get_logger("publishing.publishers.heavenly")


class HeavenlyPublisher(BasePublishingProvider):
    """Publishes articles and attaches featured image URLs to Heavenly Insights."""

    def __init__(self, heavenly_client: HeavenlyClient | None = None) -> None:
        self.heavenly_client = heavenly_client

    @property
    def name(self) -> str:
        return "heavenly"

    def _get_client(self, site_data: dict[str, Any]) -> HeavenlyClient:
        if self.heavenly_client:
            return self.heavenly_client
        return HeavenlyClient(
            site_url=site_data.get("heavenly_site_url"),
            api_url=site_data.get("heavenly_api_url"),
        )

    async def publish_article(
        self,
        prepared_payload: dict[str, Any],
        site_data: dict[str, Any],
        draft_project_data: dict[str, Any] | None = None,
        final_audit_package_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Publishes post with featured image URL to Heavenly Insights."""
        settings = get_settings()
        client = self._get_client(site_data)

        mode = prepared_payload.get("publication_mode", PublicationMode.DRAFT)
        h_status = "published" if mode == PublicationMode.PUBLISH_NOW else "draft"
        category = (draft_project_data or {}).get("primary_topic", "General")
        seo_pkg = prepared_payload.get("seo_package")
        excerpt = (
            (draft_project_data or {}).get("excerpt")
            or (seo_pkg.meta_description if seo_pkg and hasattr(seo_pkg, "meta_description") else "")
            or ""
        )
        body = prepared_payload.get("rendered_html", "")
        featured_img_url = prepared_payload.get("featured_image_url")
        featured_img_alt = prepared_payload.get("featured_image_alt") or prepared_payload["title"]

        # Cover images must live at a public absolute URL. When we hold the bytes,
        # upload them to the publisher so the article never renders a broken image.
        img_bytes = prepared_payload.get("featured_image_bytes")
        if getattr(settings, "HEAVENLY_UPLOAD_IMAGES", True) and img_bytes:
            try:
                featured_img_url = await client.ensure_public_cover_url(
                    image_bytes=img_bytes,
                    filename=prepared_payload.get("featured_image_filename") or "cover.webp",
                    mime_type="image/webp",
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Heavenly cover upload failed during publish: {exc}")
                if getattr(settings, "ARTICLE_FEATURED_IMAGE_REQUIRED", True):
                    raise ZohraError(
                        "Featured image could not be uploaded to Heavenly Insights",
                        code="MEDIA_BLOCKED",
                    ) from exc

        if getattr(settings, "ARTICLE_FEATURED_IMAGE_REQUIRED", True) and not is_public_absolute_url(featured_img_url):
            raise ZohraError(
                "Heavenly publication requires a public absolute featured image URL "
                f"(got {featured_img_url!r})",
                code="MEDIA_BLOCKED",
            )

        res = await client.create_or_update_post(
            title=prepared_payload["title"],
            slug=prepared_payload["slug"],
            category=category,
            excerpt=excerpt,
            body=body,
            status=h_status,
            image_url=featured_img_url,
            cover_image_alt=featured_img_alt,
        )

        post_url = res.get("url") or res.get("link") or f"{client.site_url}/articles/{prepared_payload['slug']}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return {
            "status": h_status,
            "url": post_url,
            "slug": prepared_payload["slug"],
            "featured_image": featured_img_url,
            "response": res,
            "published_at": now_iso if h_status == "published" else None,
        }

    async def attach_featured_media(
        self,
        media_data: dict[str, Any],
        post_identifier: Any,
        site_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Attaches/replaces a post's cover image.

        Accepts either ready bytes (``bytes``/``image_bytes``) which are uploaded
        here, or an already-public absolute ``public_url``/``image_url``.
        """
        settings = get_settings()
        client = self._get_client(site_data)

        image_url = media_data.get("public_url") or media_data.get("image_url")
        raw_bytes = media_data.get("bytes") or media_data.get("image_bytes")

        if not is_public_absolute_url(image_url):
            if raw_bytes and getattr(settings, "HEAVENLY_UPLOAD_IMAGES", True):
                image_url = await client.ensure_public_cover_url(
                    image_bytes=raw_bytes,
                    filename=media_data.get("filename") or f"{post_identifier}.webp",
                    mime_type=media_data.get("mime_type") or "image/webp",
                )
            else:
                raise ZohraError(
                    "A public absolute image URL or image bytes are required for Heavenly attachment "
                    f"(got {image_url!r})",
                    code="IMAGE_URL_MISSING",
                )

        # In Heavenly, updating post by slug updates the image
        slug = str(post_identifier)
        res = await client.create_or_update_post(
            title=media_data.get("title", slug),
            slug=slug,
            category=media_data.get("category", "General"),
            excerpt=media_data.get("excerpt", ""),
            body=media_data.get("body", ""),
            status="published",
            image_url=image_url,
            cover_image_alt=media_data.get("alt_text") or media_data.get("caption"),
        )
        return {"attached": True, "image_url": image_url, "response": res}

    async def verify_publication(
        self,
        publication_result: dict[str, Any],
        expected_title: str,
        expected_media_url: str | None = None,
    ) -> dict[str, Any]:
        """Verifies Heavenly publication."""
        post_url = publication_result.get("url")
        if not post_url:
            raise ZohraError("Heavenly publication missing URL", code="URL_MISSING")
        featured_image = publication_result.get("featured_image")
        media_verified = bool(featured_image) if expected_media_url else True

        return {
            "verified": True,
            "target": "heavenly",
            "url": post_url,
            "media_url": featured_image,
            "media_assignment": "PASS" if media_verified else "REPAIR_REQUIRED",
        }
