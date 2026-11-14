"""
Zohra — Git / Static Website Publishing Provider.

Stores generated articles in static Markdown/MDX frontmatter format and
places optimized responsive images into the website's static asset directory
(e.g., /public/images/articles/ or /storage/media/articles/).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.publishing.publishers.base import BasePublishingProvider

logger = get_logger("publishing.publishers.git_static")


class GitStaticPublisher(BasePublishingProvider):
    """Publishes articles to a Git-backed static site directory (Markdown / MDX + assets)."""

    def __init__(self, root_dir: Path | str | None = None) -> None:
        settings = get_settings()
        self.root_dir = Path(root_dir or getattr(settings, "STATIC_CONTENT_DIR", "./content/articles"))
        self.assets_dir = Path(getattr(settings, "STATIC_ASSETS_DIR", "./public/images/articles"))

    @property
    def name(self) -> str:
        return "git_static"

    def _ensure_dirs(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    async def publish_article(
        self,
        prepared_payload: dict[str, Any],
        site_data: dict[str, Any],
        draft_project_data: dict[str, Any] | None = None,
        final_audit_package_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generates and saves Markdown/MDX with frontmatter and copies/links featured media.
        """
        self._ensure_dirs()

        title = prepared_payload.get("title", "Untitled")
        slug = prepared_payload.get("slug", "untitled")
        rendered_html = prepared_payload.get("rendered_html", "")
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Extract featured media info
        featured_img_url = prepared_payload.get("featured_image_url", "")
        featured_img_alt = prepared_payload.get("featured_image_alt", "")
        featured_bytes = prepared_payload.get("featured_image_bytes")
        featured_filename = prepared_payload.get("featured_image_filename")

        # If raw image bytes provided, ensure written to static assets dir
        static_image_rel_path = ""
        if featured_bytes and featured_filename:
            dest_img = self.assets_dir / featured_filename
            dest_img.write_bytes(featured_bytes)
            static_image_rel_path = f"/images/articles/{featured_filename}"
        elif featured_img_url:
            static_image_rel_path = featured_img_url

        category = (draft_project_data or {}).get("primary_topic", site_data.get("niche", "Technology"))
        excerpt = (draft_project_data or {}).get("meta_description") or f"Comprehensive guide to {title}."

        # Frontmatter in project format
        frontmatter = [
            "---",
            f'title: "{title}"',
            f'slug: "{slug}"',
            f'date: "{now_iso}"',
            f'category: "{category}"',
            f'excerpt: "{excerpt}"',
        ]
        if static_image_rel_path:
            frontmatter.append(f'featured_image: "{static_image_rel_path}"')
        if featured_img_alt:
            frontmatter.append(f'featured_image_alt: "{featured_img_alt}"')
        frontmatter.extend([
            f'canonical_url: "{prepared_payload.get("seo_package", {}).canonical_url if hasattr(prepared_payload.get("seo_package"), "canonical_url") else ""}"',
            "status: published",
            "---",
            "",
            rendered_html,
        ])

        content_md = "\n".join(frontmatter)
        file_path = self.root_dir / f"{slug}.md"
        file_path.write_text(content_md, encoding="utf-8")

        logger.info(f"GitStaticPublisher wrote article to {file_path}")

        base_url = site_data.get("domain", "example.com")
        article_url = f"https://{base_url}/articles/{slug}"

        return {
            "status": "published",
            "file_path": str(file_path),
            "url": article_url,
            "slug": slug,
            "featured_image": static_image_rel_path,
            "featured_image_alt": featured_img_alt,
            "published_at": now_iso,
        }

    async def attach_featured_media(
        self,
        media_data: dict[str, Any],
        post_identifier: Any,
        site_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Updates or ensures static featured media asset is in place."""
        self._ensure_dirs()
        filename = media_data.get("filename", "featured.webp")
        file_bytes = media_data.get("bytes")
        if file_bytes:
            dest_img = self.assets_dir / filename
            dest_img.write_bytes(file_bytes)
        return {
            "attached": True,
            "public_url": f"/images/articles/{filename}",
            "alt_text": media_data.get("alt_text", ""),
        }

    async def verify_publication(
        self,
        publication_result: dict[str, Any],
        expected_title: str,
        expected_media_url: str | None = None,
    ) -> dict[str, Any]:
        """Checks that generated file and media asset exist on disk."""
        file_path_str = publication_result.get("file_path")
        if not file_path_str:
            raise ZohraError("Static file path missing in publication result", code="FILE_PATH_MISSING")

        file_path = Path(file_path_str)
        if not file_path.exists() or file_path.stat().st_size < 100:
            raise ZohraError(f"Static publication file missing or truncated: {file_path}", code="FILE_MISSING")

        text = file_path.read_text(encoding="utf-8")
        if expected_title not in text:
            raise ZohraError("Article title not found in published static file", code="TITLE_MISSING")

        media_verified = True
        img_rel = publication_result.get("featured_image")
        if expected_media_url or img_rel:
            target_asset = self.assets_dir / Path(img_rel or "").name
            if not target_asset.exists() or target_asset.stat().st_size == 0:
                media_verified = False

        return {
            "verified": True,
            "target": "git_static",
            "file_exists": True,
            "media_assignment": "PASS" if media_verified else "REPAIR_REQUIRED",
            "url": publication_result.get("url"),
        }
