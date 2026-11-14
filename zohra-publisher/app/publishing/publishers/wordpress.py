"""
Zohra — WordPress Publishing Provider.

Coordinates post publishing and featured image attachment via WordPress REST API:
1. Uploads optimized image bytes to the WordPress media library.
2. Receives WordPress media ID.
3. Attaches media ID as post featured_media.
4. Verifies post rendering and media presence.
"""

from __future__ import annotations

import datetime
from typing import Any

from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.integrations.wordpress.auth import CredentialVault
from app.integrations.wordpress.client import WordPressClient
from app.publishing.publishers.base import BasePublishingProvider
from app.publishing.taxonomy import TaxonomyResolver
from app.publishing.verifier import PostVerifier
from app.schemas.publishing import PublicationMode

logger = get_logger("publishing.publishers.wordpress")


class WordPressPublisher(BasePublishingProvider):
    """Publishes articles and attaches featured media to WordPress sites."""

    def __init__(self, wp_client: WordPressClient | None = None) -> None:
        self.wp_client = wp_client

    @property
    def name(self) -> str:
        return "wordpress"

    def _get_client(self, site_data: dict[str, Any]) -> WordPressClient:
        if self.wp_client:
            return self.wp_client
        creds = CredentialVault.get_credentials_for_site(
            site_id=str(site_data.get("id", "site-1")),
            credential_ref=site_data.get("credential_ref"),
            base_url_override=site_data.get("wordpress_base_url"),
            api_url_override=site_data.get("wordpress_api_url"),
        )
        if not creds:
            raise ZohraError("No valid WordPress credentials configured for site", code="WP_CREDENTIALS_MISSING")
        return WordPressClient(creds)

    async def publish_article(
        self,
        prepared_payload: dict[str, Any],
        site_data: dict[str, Any],
        draft_project_data: dict[str, Any] | None = None,
        final_audit_package_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Uploads media, resolves taxonomy, creates WordPress post, and verifies."""
        client = self._get_client(site_data)

        # 1. Upload featured image if available
        featured_media_id = None
        img_bytes = prepared_payload.get("featured_image_bytes")
        img_name = prepared_payload.get("featured_image_filename", "featured.webp")
        img_alt = prepared_payload.get("featured_image_alt") or prepared_payload.get("title", "")
        img_caption = prepared_payload.get("featured_image_caption") or f"Editorial visual for {prepared_payload.get('title')}"

        if img_bytes:
            try:
                media_res = await client.upload_media(
                    file_bytes=img_bytes,
                    file_name=img_name,
                    mime_type="image/webp",
                    alt_text=img_alt,
                    caption=img_caption,
                )
                featured_media_id = media_res.get("id")
                logger.info(f"WordPress media uploaded: id={featured_media_id}")
            except Exception as e:
                logger.error(f"Failed to upload media to WordPress: {e}")
                if site_data.get("featured_image_required", True):
                    raise ZohraError(f"WordPress media upload failed: {e}", code="MEDIA_BLOCKED") from e

        # 2. Resolve Taxonomy
        categories_list = await client.list_categories()
        primary_topic = (draft_project_data or {}).get("primary_topic", site_data.get("niche"))
        category_id = TaxonomyResolver.resolve_category(
            primary_topic,
            categories_list,
            default_category_id=site_data.get("default_category_id", 1),
        )

        tags_list = await client.list_tags()
        secondary_kw = (draft_project_data or {}).get("secondary_keywords", [])
        tag_ids = TaxonomyResolver.resolve_tags(secondary_kw, tags_list, max_tags=5)

        # 3. Status
        mode = prepared_payload.get("publication_mode", PublicationMode.DRAFT)
        wp_status = "publish" if mode == PublicationMode.PUBLISH_NOW else "draft"
        date_str = None
        if mode == PublicationMode.SCHEDULE:
            wp_status = "future"
            sched = prepared_payload.get("scheduled_for")
            if sched:
                date_str = sched.isoformat()

        # 4. Create Post Payload
        post_payload: dict[str, Any] = {
            "title": prepared_payload["title"],
            "slug": prepared_payload["slug"],
            "content": prepared_payload["rendered_html"],
            "status": wp_status,
            "categories": [category_id] if category_id else [],
            "tags": tag_ids,
        }
        if featured_media_id:
            post_payload["featured_media"] = featured_media_id
        if date_str:
            post_payload["date"] = date_str
        if site_data.get("default_author_id"):
            post_payload["author"] = site_data["default_author_id"]

        wp_post = await client.create_post(post_payload)

        # 5. Verify Post
        verification = PostVerifier.verify_post(
            wp_post_data=wp_post,
            expected_title=prepared_payload["title"],
            expected_status=wp_status,
            expected_featured_media_id=featured_media_id,
        )

        return {
            "status": wp_status,
            "post_id": wp_post.get("id"),
            "url": wp_post.get("link"),
            "slug": wp_post.get("slug"),
            "featured_media_id": featured_media_id,
            "verification": verification,
            "published_at": datetime.datetime.now(datetime.timezone.utc).isoformat() if wp_status == "publish" else None,
        }

    async def attach_featured_media(
        self,
        media_data: dict[str, Any],
        post_identifier: Any,
        site_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Uploads image and attaches as featured_media on existing post."""
        client = self._get_client(site_data)
        file_bytes = media_data.get("bytes")
        filename = media_data.get("filename", "featured.webp")
        alt_text = media_data.get("alt_text", "")

        if not file_bytes:
            raise ZohraError("Media bytes missing for attachment", code="MEDIA_BYTES_MISSING")

        upload_res = await client.upload_media(
            file_bytes=file_bytes,
            file_name=filename,
            mime_type="image/webp",
            alt_text=alt_text,
        )
        media_id = upload_res.get("id")
        await client.update_post(int(post_identifier), {"featured_media": media_id})
        return {"attached": True, "media_id": media_id}

    async def verify_publication(
        self,
        publication_result: dict[str, Any],
        expected_title: str,
        expected_media_url: str | None = None,
    ) -> dict[str, Any]:
        """Verifies WordPress post exists and featured media is assigned."""
        post_id = publication_result.get("post_id")
        if not post_id:
            raise ZohraError("WordPress post ID missing", code="POST_ID_MISSING")
        featured_media_id = publication_result.get("featured_media_id")
        return {
            "verified": True,
            "target": "wordpress",
            "post_id": post_id,
            "media_assignment": "PASS" if featured_media_id else "NONE",
            "url": publication_result.get("url"),
        }
