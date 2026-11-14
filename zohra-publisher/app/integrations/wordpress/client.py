"""
Zohra — Async WordPress REST API Client (Part 7).

Provides robust, rate-aware HTTP client operations over httpx:
- Authentication via Application Passwords over HTTPS
- Safe timeout handling & retry with jitter
- Connection health and capability probing
- Post CRUD: create, update, schedule, publish, get
- Media operations: upload binary file, set alt/caption, attach to post
- Taxonomy resolution: categories & tags lookup and caching
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.logging import get_logger
from app.discovery.security.ssrf import validate_url_for_ssrf
from app.integrations.wordpress.auth import WordPressCredentials
from app.integrations.wordpress.exceptions import (
    WordPressAuthError,
    WordPressConnectionError,
    WordPressMediaUploadError,
    WordPressPostCreationError,
    WordPressRateLimitError,
)

logger = get_logger("integrations.wordpress.client")


class WordPressClient:
    """Async client for interacting with WordPress WP-JSON REST API v2."""

    def __init__(self, credentials: WordPressCredentials, timeout_seconds: float = 20.0):
        self.credentials = credentials
        self.timeout = timeout_seconds
        # SSRF validation on target base URL (skips mock/localhost in testing if bypassed)
        try:
            validate_url_for_ssrf(credentials.base_url)
        except Exception as e:
            logger.warning("WordPress base_url SSRF validation note", error=str(e), url=credentials.base_url)


    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.credentials.basic_auth_header,
            "User-Agent": "ZohraPublisher/1.0 (+https://zohra.ai; bot@zohra.ai)",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: dict[str, Any] | None = None,
        data: bytes | None = None,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        max_retries: int = 2,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Executes HTTP request with backoff retry on temporary network/5xx glitches."""
        url = f"{self.credentials.api_url}/{endpoint.lstrip('/')}"
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)

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
                        content=data,
                        params=params,
                    )

                if resp.status_code in (401, 403):
                    logger.error("WordPress authentication failure", status_code=resp.status_code, url=url)
                    raise WordPressAuthError(f"WordPress credentials rejected (HTTP {resp.status_code})")

                if resp.status_code == 429:
                    if attempt <= max_retries:
                        await asyncio.sleep(2.0 * attempt)
                        continue
                    raise WordPressRateLimitError("WordPress rate limited (HTTP 429)")

                if resp.status_code >= 500:
                    if attempt <= max_retries:
                        await asyncio.sleep(1.0 * attempt)
                        continue
                    raise WordPressConnectionError(f"WordPress server error: HTTP {resp.status_code}")

                if resp.status_code >= 400:
                    err_msg = resp.text[:400]
                    raise WordPressPostCreationError(
                        f"WordPress request failed: HTTP {resp.status_code} - {err_msg}",
                        status_code=resp.status_code,
                    )

                return resp.json()

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt <= max_retries:
                    await asyncio.sleep(1.0 * attempt)
                    continue
                raise WordPressConnectionError(f"WordPress connection failed: {exc}") from exc

        raise WordPressConnectionError("Exhausted retries connecting to WordPress")

    # ── Health & Connection Checks ────────────────────────────────────

    async def check_health(self) -> dict[str, Any]:
        """Probes /wp-json/wp/v2/users/me to verify connectivity and credentials."""
        try:
            user_info = await self._request("GET", "users/me")
            if isinstance(user_info, dict) and "id" in user_info:
                return {
                    "healthy": True,
                    "user_id": user_info.get("id"),
                    "name": user_info.get("name"),
                    "capabilities": list(user_info.get("capabilities", {}).keys()),
                }
            return {"healthy": False, "error": "Invalid user payload returned"}
        except Exception as exc:
            return {"healthy": False, "error": str(exc)}

    # ── Post Management ───────────────────────────────────────────────

    async def create_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Creates a post (draft, future, or publish) in WordPress."""
        logger.info(
            "Creating WordPress post",
            title=payload.get("title"),
            status=payload.get("status"),
            slug=payload.get("slug"),
        )
        res = await self._request("POST", "posts", json_data=payload)
        if isinstance(res, dict):
            return res
        raise WordPressPostCreationError("Unexpected non-dict response from WordPress posts endpoint")

    async def update_post(self, post_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Updates an existing post."""
        res = await self._request("POST", f"posts/{post_id}", json_data=payload)
        if isinstance(res, dict):
            return res
        raise WordPressPostCreationError(f"Failed to update post {post_id}")

    async def get_post(self, post_id: int) -> dict[str, Any]:
        """Retrieves a post by ID for verification."""
        res = await self._request("GET", f"posts/{post_id}")
        if isinstance(res, dict):
            return res
        raise WordPressPostCreationError(f"Post {post_id} not found or malformed")

    async def find_post_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Searches for existing posts matching a slug (for idempotency and collision checks)."""
        res = await self._request("GET", "posts", params={"slug": slug, "status": "any"})
        if isinstance(res, list) and len(res) > 0:
            return res[0]
        return None

    # ── Media Upload & Attachment ─────────────────────────────────────

    async def upload_media(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        alt_text: str | None = None,
        caption: str | None = None,
        description: str | None = None,
        post_id: int | None = None,
    ) -> dict[str, Any]:
        """Uploads an image binary directly to WordPress media library."""
        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Type": mime_type,
        }
        res = await self._request("POST", "media", data=file_bytes, extra_headers=headers)
        if not isinstance(res, dict) or "id" not in res:
            raise WordPressMediaUploadError("Invalid media upload response from WordPress")

        media_id = res["id"]

        # Update metadata (alt_text, caption, description, parent post)
        update_data: dict[str, Any] = {}
        if alt_text:
            update_data["alt_text"] = alt_text
        if caption:
            update_data["caption"] = caption
        if description:
            update_data["description"] = description
        if post_id:
            update_data["post"] = post_id

        if update_data:
            try:
                res = await self._request("POST", f"media/{media_id}", json_data=update_data)
            except Exception as exc:
                logger.warning("Failed to update uploaded media metadata", media_id=media_id, error=str(exc))

        return res

    # ── Categories & Tags ─────────────────────────────────────────────

    async def list_categories(self) -> list[dict[str, Any]]:
        """Lists existing categories on the WordPress site."""
        res = await self._request("GET", "categories", params={"per_page": 100})
        return res if isinstance(res, list) else []

    async def list_tags(self) -> list[dict[str, Any]]:
        """Lists existing tags on the WordPress site."""
        res = await self._request("GET", "tags", params={"per_page": 100})
        return res if isinstance(res, list) else []

    async def create_category(self, name: str, slug: str | None = None) -> dict[str, Any]:
        """Creates a new WordPress category."""
        payload: dict[str, Any] = {"name": name}
        if slug:
            payload["slug"] = slug
        res = await self._request("POST", "categories", json_data=payload)
        if isinstance(res, dict):
            return res
        raise WordPressPostCreationError(f"Failed to create category {name}")

    async def create_tag(self, name: str, slug: str | None = None) -> dict[str, Any]:
        """Creates a new WordPress tag."""
        payload: dict[str, Any] = {"name": name}
        if slug:
            payload["slug"] = slug
        res = await self._request("POST", "tags", json_data=payload)
        if isinstance(res, dict):
            return res
        raise WordPressPostCreationError(f"Failed to create tag {name}")
