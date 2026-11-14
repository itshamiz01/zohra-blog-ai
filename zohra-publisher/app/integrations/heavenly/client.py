"""
Zohra — Heavenly Insights Publishing API Client.

Features:
- Bearer token authentication over HTTPS.
- Never exposes tokens in logs, console, or representations.
- SSRF validation on API and Site URLs.
- Idempotent article publishing & updating (same slug updates existing article).
- Robust retries with exponential backoff on transient network and 5xx errors.
- Plain text formatting with double newlines between paragraphs.
- Draft verification and production publishing modes.
- Listing of all drafts and published articles via GET /api/posts.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.discovery.security.ssrf import validate_url_for_ssrf
from app.integrations.heavenly.exceptions import (
    HeavenlyAuthError,
    HeavenlyConnectionError,
    HeavenlyImageUploadError,
    HeavenlyPostError,
    HeavenlyRateLimitError,
    HeavenlyValidationError,
)
from app.integrations.heavenly.formatter import format_plain_text_body

logger = get_logger("integrations.heavenly.client")


def is_public_absolute_url(url: str | None) -> bool:
    """
    True only for an absolute http(s) URL that a reader's browser can load.

    Relative paths such as "/storage/media/articles/cover.webp" are rejected:
    they resolve against the *target blog's* domain, where no such file exists.
    """
    if not url:
        return False
    candidate = url.strip()
    if not candidate.lower().startswith(("http://", "https://")):
        return False
    # Localhost / app-internal bases are unreachable from the public blog.
    lowered = candidate.lower()
    for blocked in ("://localhost", "://127.0.0.1", "://0.0.0.0", "://[::1]"):
        if blocked in lowered:
            return False
    return True



class HeavenlyClient:
    """
    Async client for publishing and managing articles on Heavenly Insights.
    """

    def __init__(
        self,
        site_url: str | None = None,
        api_url: str | None = None,
        token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        settings = get_settings()

        self.site_url = (
            site_url
            or getattr(settings, "HEAVENLY_SITE_URL", None)
            or "https://heavenly-insights-educator.hamidansari1795.chatgpt.site"
        ).rstrip("/")

        self.api_url = (
            api_url
            or getattr(settings, "HEAVENLY_API_URL", None)
            or f"{self.site_url}/api/posts"
        ).rstrip("/")

        # Cover/featured image upload endpoint (multipart/form-data, field name "file").
        # The read-only twin lives at GET {images_url}/{id} and is publicly fetchable.
        self.images_url = f"{self.site_url}/api/images"

        raw_token = token or getattr(settings, "HEAVENLY_API_TOKEN", None) or ""
        self._token = raw_token.strip()
        self.timeout = timeout_seconds

        # SSRF validation on base URL
        try:
            validate_url_for_ssrf(self.site_url)
        except Exception as e:
            logger.warning(f"Heavenly site_url SSRF validation notice: {e} (url={self.site_url})")

    def __repr__(self) -> str:
        # Mask the token completely in any representation
        has_token = bool(self._token and self._token != "PASTE_GENERATED_TOKEN_HERE")
        return f"<HeavenlyClient site_url='{self.site_url}' api_url='{self.api_url}' token_configured={has_token}>"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def is_configured(self) -> bool:
        """Returns True if a real token (not placeholder) is configured."""
        return bool(self._token and self._token != "PASTE_GENERATED_TOKEN_HERE")

    def _get_headers(self) -> dict[str, str]:
        """Builds HTTP headers with Bearer token. Never log this output."""
        if not self._token or self._token == "PASTE_GENERATED_TOKEN_HERE":
            raise HeavenlyAuthError(
                "HEAVENLY_API_TOKEN is not configured or still set to placeholder in .env. "
                "Please generate a token from your Heavenly admin panel and update .env."
            )

        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ZohraPublisher/1.0 (+https://zohra.ai; bot@zohra.ai)",
        }

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        max_retries: int = 2,
    ) -> Any:
        """
        Executes HTTP request with backoff retry on temporary network or 5xx glitches.
        Guarantees that token is never logged.
        """
        headers = self._get_headers()
        attempt = 0

        while attempt <= max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=json_data,
                        params=params,
                    )

                if resp.status_code in (401, 403):
                    logger.error(
                        f"Heavenly Insights authentication failure: HTTP {resp.status_code} at {url}"
                    )
                    raise HeavenlyAuthError(
                        f"Heavenly Insights credentials rejected (HTTP {resp.status_code}). Verify your token."
                    )

                if resp.status_code == 429:
                    if attempt <= max_retries:
                        backoff = 2.0 * attempt
                        logger.warning(
                            f"Heavenly Insights rate limited (429), retrying in {backoff}s (attempt {attempt})"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise HeavenlyRateLimitError("Heavenly Insights rate limited (HTTP 429)")

                if resp.status_code >= 500:
                    if attempt <= max_retries:
                        backoff = 1.0 * attempt
                        logger.warning(
                            f"Heavenly Insights server error: HTTP {resp.status_code}, retrying (attempt {attempt})"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise HeavenlyConnectionError(
                        f"Heavenly Insights server error: HTTP {resp.status_code}"
                    )

                if resp.status_code >= 400:
                    err_msg = resp.text[:400]
                    logger.error(
                        f"Heavenly Insights client error: HTTP {resp.status_code} - {err_msg}"
                    )
                    raise HeavenlyPostError(
                        f"Heavenly Insights request failed (HTTP {resp.status_code}): {err_msg}",
                        status_code=resp.status_code,
                    )

                # Success
                try:
                    return resp.json()
                except Exception:
                    return {"status": "ok", "raw": resp.text}

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt <= max_retries:
                    backoff = 1.5 * attempt
                    logger.warning(
                        f"Heavenly Insights connection attempt failed, retrying in {backoff}s: {exc}"
                    )
                    await asyncio.sleep(backoff)
                    continue
                raise HeavenlyConnectionError(
                    f"Heavenly Insights connection failed after {max_retries} retries: {exc}"
                ) from exc

        raise HeavenlyConnectionError("Exhausted retries connecting to Heavenly Insights API")

    # ── Post Management ───────────────────────────────────────────────

    async def upload_image(
        self,
        file_bytes: bytes,
        filename: str = "cover.webp",
        mime_type: str = "image/webp",
        *,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """
        Uploads an image to Heavenly Insights and returns its PUBLIC url.

        Contract (verified live against the Heavenly Insights host):
            POST {site_url}/api/images   multipart/form-data, field name = "file"
            201 -> {"id": "...", "url": "https://<site>/api/images/<id>", "mime": "...", "size": N}

        The returned ``url`` is an absolute, publicly fetchable URL that the
        published article page renders verbatim inside ``<img src="...">``.
        Every article must call this before publishing so the cover actually
        resolves for readers (a relative "/storage/..." path never does).

        Raises:
            HeavenlyImageUploadError: on any non-2xx, network, or empty-payload failure.
        """
        if not file_bytes:
            raise HeavenlyImageUploadError("Cannot upload empty image bytes")

        headers = self._get_headers()
        # httpx sets the multipart Content-Type (with boundary) itself.
        headers.pop("Content-Type", None)

        safe_name = (filename or "cover.webp").strip() or "cover.webp"
        attempt = 0
        last_error: str = "unknown error"

        while attempt <= max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=max(self.timeout, 60.0)) as client:
                    resp = await client.post(
                        self.images_url,
                        headers=headers,
                        files={"file": (safe_name, file_bytes, mime_type or "image/webp")},
                    )

                if resp.status_code in (401, 403):
                    raise HeavenlyAuthError(
                        f"Heavenly Insights rejected the image upload (HTTP {resp.status_code}). Verify your token."
                    )

                if resp.status_code == 429 or resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code}"
                    if attempt <= max_retries:
                        backoff = 1.5 * attempt
                        logger.warning(
                            f"Heavenly image upload transient failure ({last_error}), retrying in {backoff}s "
                            f"(attempt {attempt}/{max_retries + 1})"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise HeavenlyImageUploadError(
                        f"Heavenly image upload failed after {attempt} attempts: {last_error}",
                        status_code=resp.status_code,
                    )

                if resp.status_code >= 400:
                    raise HeavenlyImageUploadError(
                        f"Heavenly image upload rejected (HTTP {resp.status_code}): {resp.text[:300]}",
                        status_code=resp.status_code,
                    )

                try:
                    data = resp.json()
                except Exception as exc:  # noqa: BLE001
                    raise HeavenlyImageUploadError(
                        f"Heavenly image upload returned non-JSON response: {resp.text[:200]}"
                    ) from exc

                public_url = (data or {}).get("url")
                if not public_url:
                    raise HeavenlyImageUploadError(
                        f"Heavenly image upload succeeded but returned no url: {str(data)[:200]}"
                    )

                logger.info(
                    f"Uploaded cover image to Heavenly Insights ({len(file_bytes)} bytes) -> {public_url}"
                )
                return dict(data)

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = str(exc)
                if attempt <= max_retries:
                    backoff = 1.5 * attempt
                    logger.warning(
                        f"Heavenly image upload connection error, retrying in {backoff}s: {exc}"
                    )
                    await asyncio.sleep(backoff)
                    continue
                raise HeavenlyImageUploadError(
                    f"Heavenly image upload connection failed after {attempt} attempts: {exc}"
                ) from exc

        raise HeavenlyImageUploadError(f"Heavenly image upload exhausted retries: {last_error}")

    async def ensure_public_cover_url(
        self,
        *,
        image_bytes: bytes | None = None,
        candidate_url: str | None = None,
        filename: str = "cover.webp",
        mime_type: str = "image/webp",
    ) -> str | None:
        """
        Returns a PUBLIC, absolute cover-image URL for a post.

        Guarantees the returned URL can actually be loaded by a reader's browser:
          1. An already-absolute http(s) URL that is not a local app path is reused.
          2. Otherwise the supplied bytes are uploaded to Heavenly Insights.
          3. A relative/local path (e.g. "/storage/media/articles/x.webp") is NEVER
             returned, because it resolves to nothing on the target blog.

        Note: an uploaded image only becomes anonymously fetchable once the post
        that references it is *published* (drafts and orphans return 404). Call
        :meth:`verify_cover_image_public` after publishing to confirm.
        """
        if candidate_url and is_public_absolute_url(candidate_url):
            return candidate_url

        if image_bytes:
            uploaded = await self.upload_image(image_bytes, filename=filename, mime_type=mime_type)
            return uploaded.get("url")

        if candidate_url:
            logger.warning(
                f"Cover image URL '{candidate_url}' is not a public absolute URL and no image bytes "
                f"were supplied; the article would render a broken image."
            )
        return None

    async def verify_cover_image_public(
        self,
        image_url: str | None,
        *,
        attempts: int = 4,
        delay_seconds: float = 1.5,
    ) -> bool:
        """
        Confirms an article's cover image is anonymously fetchable by a reader.

        Must be called AFTER the post is published: Heavenly Insights serves an
        uploaded image at ``/api/images/<id>`` only once a published post
        references it (draft/orphan images return 404).

        Returns True on the first successful fetch, False if every attempt fails.
        Never raises — a failed check is a monitoring signal, not a crash.
        """
        if not is_public_absolute_url(image_url):
            logger.warning(f"Cannot verify cover image: not a public absolute URL ({image_url!r})")
            return False

        for attempt in range(1, max(attempts, 1) + 1):
            try:
                async with httpx.AsyncClient(timeout=min(self.timeout, 20.0), follow_redirects=True) as client:
                    resp = await client.get(image_url)
                if resp.status_code == 200 and resp.content:
                    logger.info(
                        f"Cover image verified publicly fetchable ({len(resp.content)} bytes): {image_url}"
                    )
                    return True
                logger.warning(
                    f"Cover image not yet fetchable (HTTP {resp.status_code}), "
                    f"attempt {attempt}/{attempts}: {image_url}"
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Cover image verification error (attempt {attempt}/{attempts}): {exc}")

            if attempt < attempts:
                await asyncio.sleep(delay_seconds)

        logger.error(f"Cover image could NOT be verified as public after {attempts} attempts: {image_url}")
        return False

    async def create_or_update_post(
        self,
        title: str,
        slug: str,
        category: str,
        excerpt: str,
        body: str,
        status: str = "draft",
        image_url: str | None = None,
        cover_image_alt: str | None = None,
    ) -> dict[str, Any]:
        """
        Creates or updates an article on Heavenly Insights.

        Args:
            title: Headline of the article
            slug: URL-safe identifier (same slug updates existing article)
            category: Category name (e.g. "Books", "Technology")
            excerpt: Short summary of the article
            body: Article content (will be formatted to plain text with blank lines)
            status: "draft" (saved in workspace) or "published" (public live)
            image_url: PUBLIC absolute URL of the cover image. Sent as
                ``cover_image_url`` — the only field the Heavenly API reads.
            cover_image_alt: Accessible alt text for the cover image.

        Returns:
            API response dictionary (contains url if published).
        """
        if not title or not title.strip():
            raise HeavenlyValidationError("Article title cannot be empty")
        if not slug or not slug.strip():
            raise HeavenlyValidationError("Article slug cannot be empty")
        if not body or not body.strip():
            raise HeavenlyValidationError("Article body cannot be empty")

        clean_status = status.strip().lower()
        if clean_status not in ("draft", "published"):
            raise HeavenlyValidationError(
                f"Invalid status '{status}'. Heavenly Insights only accepts 'draft' or 'published'."
            )

        # Body must be plain text with blank line (\n\n) between paragraphs
        formatted_body = format_plain_text_body(body)

        payload = {
            "title": title.strip(),
            "slug": slug.strip(),
            "category": category.strip() if category else "General",
            "excerpt": excerpt.strip() if excerpt else "",
            "body": formatted_body,
            "status": clean_status,
        }

        # The Heavenly Insights post schema exposes exactly: cover_image_url, cover_image_alt.
        # Legacy "featured_image" / "image_url" keys are silently discarded by the API,
        # which is why covers used to go missing.
        if image_url:
            payload["cover_image_url"] = image_url
            payload["cover_image_alt"] = (cover_image_alt or "").strip()
        elif cover_image_alt:
            payload["cover_image_alt"] = cover_image_alt.strip()

        logger.info(
            f"Sending post to Heavenly Insights: title='{payload['title']}', slug='{payload['slug']}', "
            f"category='{payload['category']}', status='{payload['status']}', "
            f"cover_image_url='{payload.get('cover_image_url', '<none>')}'"
        )

        res = await self._request("POST", self.api_url, json_data=payload)
        if isinstance(res, dict):
            return res
        return {"status": "success", "data": res}

    async def create_draft(
        self,
        title: str,
        slug: str,
        category: str,
        excerpt: str,
        body: str,
        image_url: str | None = None,
        cover_image_alt: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to save article as draft."""
        return await self.create_or_update_post(
            title=title,
            slug=slug,
            category=category,
            excerpt=excerpt,
            body=body,
            status="draft",
            image_url=image_url,
            cover_image_alt=cover_image_alt,
        )

    async def publish_post(
        self,
        title: str,
        slug: str,
        category: str,
        excerpt: str,
        body: str,
        image_url: str | None = None,
        cover_image_alt: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to publish article live."""
        return await self.create_or_update_post(
            title=title,
            slug=slug,
            category=category,
            excerpt=excerpt,
            body=body,
            status="published",
            image_url=image_url,
            cover_image_alt=cover_image_alt,
        )

    async def list_posts(self) -> list[dict[str, Any]] | dict[str, Any]:
        """
        Fetches all posts (drafts and published) using GET /api/posts with Bearer token.
        """
        logger.info("Listing posts from Heavenly Insights")
        return await self._request("GET", self.api_url)

    async def verify_draft_flow(
        self,
        title: str = "How to Build a Daily Reading Habit",
        slug: str = "how-to-build-a-daily-reading-habit",
        category: str = "Books",
        excerpt: str = "Practical steps to make reading part of your daily routine.",
        body: str = "First paragraph.\n\nSecond paragraph.",
    ) -> dict[str, Any]:
        """
        Tests creating a draft and verifies the response.
        Useful for sanity checks before triggering production runs.
        """
        logger.info(f"Initiating Heavenly draft verification flow for slug '{slug}'")
        result = await self.create_draft(
            title=title,
            slug=slug,
            category=category,
            excerpt=excerpt,
            body=body,
        )
        return {
            "verified": True,
            "status": "draft",
            "slug": slug,
            "response": result,
        }

    async def check_health(self) -> dict[str, Any]:
        """
        Verifies connectivity and token validity against Heavenly Insights.
        """
        if not self.is_configured:
            return {
                "healthy": False,
                "configured": False,
                "error": "HEAVENLY_API_TOKEN is not configured in .env",
            }

        try:
            posts = await self.list_posts()
            count = len(posts) if isinstance(posts, list) else len(posts.get("posts", [])) if isinstance(posts, dict) else 0
            return {
                "healthy": True,
                "configured": True,
                "site_url": self.site_url,
                "api_url": self.api_url,
                "posts_count": count,
            }
        except Exception as exc:
            return {
                "healthy": False,
                "configured": True,
                "site_url": self.site_url,
                "error": str(exc),
            }
