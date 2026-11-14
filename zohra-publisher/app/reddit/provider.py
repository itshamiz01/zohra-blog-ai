"""
Zohra — Reddit Provider Abstraction.

Implements official, supported Reddit integration:
- Public read-only JSON endpoints for unauthenticated question discovery and rules inspection.
- OAuth 2.0 bearer authentication when client credentials are provided.
- Strict rate limiting adhering to Reddit API guidelines.
- Full credential redaction in representation, logs, and exceptions.
- Never scrapes restricted data, circumvents access controls, or uses browser automation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.reddit.exceptions import (
    RedditAuthError,
    RedditPostNotFoundError,
    RedditRateLimitError,
    RedditUnavailableError,
)

logger = get_logger("reddit.provider")

REDDIT_BASE_URL = "https://www.reddit.com"
REDDIT_OAUTH_URL = "https://oauth.reddit.com"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"


class RedditProvider:
    """Official Reddit integration provider supporting discovery and rule retrieval."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        settings = get_settings()
        self._client_id = client_id or getattr(settings, "REDDIT_CLIENT_ID", None) or ""
        self._client_secret = client_secret or getattr(settings, "REDDIT_CLIENT_SECRET", None) or ""
        self._user_agent = user_agent or getattr(
            settings, "REDDIT_USER_AGENT", "ZohraBot/1.0 (Content Intelligence; by /u/ZohraAI)"
        )
        self._username = username or getattr(settings, "REDDIT_USERNAME", None) or ""
        self._password = password or getattr(settings, "REDDIT_PASSWORD", None) or ""
        self.timeout = timeout

        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._rate_limit_remaining: float = 60.0
        self._rate_limit_reset: float = 0.0

    def __repr__(self) -> str:
        # Strict credential redaction
        has_oauth = bool(self._client_id and self._client_secret)
        mode = "oauth" if has_oauth else "read_only_public"
        return f"<RedditProvider mode={mode} user_agent='{self._user_agent}'>"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def is_oauth_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    async def _get_auth_headers(self) -> dict[str, str]:
        """Obtain headers, refreshing OAuth token if configured."""
        headers = {"User-Agent": self._user_agent}

        if not self.is_oauth_configured:
            return headers

        now = time.time()
        if self._access_token and now < self._token_expires_at - 60.0:
            headers["Authorization"] = f"Bearer {self._access_token}"
            return headers

        # Obtain OAuth token via client credentials or script flow
        try:
            data = {"grant_type": "client_credentials"}
            if self._username and self._password:
                data = {
                    "grant_type": "password",
                    "username": self._username,
                    "password": self._password,
                }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    REDDIT_TOKEN_URL,
                    auth=(self._client_id, self._client_secret),
                    data=data,
                    headers={"User-Agent": self._user_agent},
                )

            if resp.status_code == 200:
                token_data = resp.json()
                self._access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = now + expires_in
                headers["Authorization"] = f"Bearer {self._access_token}"
                return headers

            logger.warning("Reddit OAuth token request failed with status %d", resp.status_code)
            raise RedditAuthError(f"Reddit OAuth authentication failed (HTTP {resp.status_code})")

        except Exception as exc:
            if isinstance(exc, RedditAuthError):
                raise
            raise RedditAuthError(f"Failed to authenticate with Reddit: {exc}") from exc

    def _update_rate_limits(self, headers: httpx.Headers) -> None:
        """Parse rate limit headers from Reddit response."""
        remaining = headers.get("x-ratelimit-remaining")
        reset_val = headers.get("x-ratelimit-reset")
        if remaining:
            try:
                self._rate_limit_remaining = float(remaining)
            except ValueError:
                pass
        if reset_val:
            try:
                self._rate_limit_reset = float(reset_val)
            except ValueError:
                pass

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform request respecting rate limits and handling standard HTTP errors."""
        if self._rate_limit_remaining < 2.0 and self._rate_limit_reset > 0:
            sleep_time = min(self._rate_limit_reset, 5.0)
            logger.info("Reddit rate limit near exhaustion, backing off for %.1fs", sleep_time)
            await asyncio.sleep(sleep_time)

        headers = await self._get_auth_headers()
        base_url = REDDIT_OAUTH_URL if "Authorization" in headers else REDDIT_BASE_URL
        url = f"{base_url}{path}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )

            self._update_rate_limits(resp.headers)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 404:
                raise RedditPostNotFoundError(f"Reddit resource not found at {path}")

            if resp.status_code in (401, 403):
                raise RedditAuthError(f"Access denied to Reddit endpoint {path} (HTTP {resp.status_code})")

            if resp.status_code == 429:
                reset_sec = self._rate_limit_reset or 60.0
                raise RedditRateLimitError(
                    f"Reddit rate limit hit. Reset in {reset_sec}s",
                    retry_after_seconds=reset_sec,
                )

            if resp.status_code in (500, 502, 503, 504):
                raise RedditUnavailableError(f"Reddit server error (HTTP {resp.status_code})")

            raise RedditUnavailableError(f"Unexpected Reddit API response (HTTP {resp.status_code})")

        except (RedditAuthError, RedditPostNotFoundError, RedditRateLimitError, RedditUnavailableError):
            raise
        except Exception as exc:
            logger.error("Reddit request network failure: %s", exc)
            raise RedditUnavailableError(f"Network error connecting to Reddit: {exc}") from exc

    # ── Discovery Operations ─────────────────────────────────────────

    async def discover_posts(
        self,
        subreddit: str,
        sort: str = "new",
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """
        Discover recent posts from a specific subreddit.
        Supports sorts: new, hot, rising, top.
        """
        clean_sub = subreddit.strip().lstrip("r/").rstrip("/")
        path = f"/r/{clean_sub}/{sort}.json"
        params = {"limit": min(limit, 100), "raw_json": 1}

        data = await self._request("GET", path, params=params)
        children = data.get("data", {}).get("children", [])

        results = []
        for child in children:
            post = child.get("data", {})
            created_utc = post.get("created_utc", 0)
            results.append({
                "reddit_post_id": post.get("id"),
                "name": post.get("name"),
                "subreddit": post.get("subreddit"),
                "author": post.get("author"),
                "title": post.get("title", ""),
                "body": post.get("selftext", ""),
                "permalink": post.get("permalink", ""),
                "url": post.get("url", f"https://reddit.com{post.get('permalink', '')}"),
                "score": post.get("score", 0),
                "upvote_ratio": post.get("upvote_ratio", 1.0),
                "comment_count": post.get("num_comments", 0),
                "flair": post.get("link_flair_text"),
                "is_self": post.get("is_self", True),
                "is_locked": post.get("locked", False),
                "is_archived": post.get("archived", False),
                "over_18": post.get("over_18", False),
                "created_at": datetime.fromtimestamp(created_utc, tz=timezone.utc),
            })
        return results

    async def search_posts(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "new",
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search posts by query across Reddit or within a specific subreddit."""
        if subreddit:
            clean_sub = subreddit.strip().lstrip("r/").rstrip("/")
            path = f"/r/{clean_sub}/search.json"
            params = {"q": query, "restrict_sr": 1, "sort": sort, "limit": min(limit, 100), "raw_json": 1}
        else:
            path = "/search.json"
            params = {"q": query, "sort": sort, "limit": min(limit, 100), "raw_json": 1}

        data = await self._request("GET", path, params=params)
        children = data.get("data", {}).get("children", [])

        results = []
        for child in children:
            post = child.get("data", {})
            created_utc = post.get("created_utc", 0)
            results.append({
                "reddit_post_id": post.get("id"),
                "name": post.get("name"),
                "subreddit": post.get("subreddit"),
                "author": post.get("author"),
                "title": post.get("title", ""),
                "body": post.get("selftext", ""),
                "permalink": post.get("permalink", ""),
                "url": post.get("url", f"https://reddit.com{post.get('permalink', '')}"),
                "score": post.get("score", 0),
                "comment_count": post.get("num_comments", 0),
                "flair": post.get("link_flair_text"),
                "is_locked": post.get("locked", False),
                "created_at": datetime.fromtimestamp(created_utc, tz=timezone.utc),
            })
        return results

    async def fetch_post(self, post_id: str, subreddit: str | None = None) -> dict[str, Any]:
        """Fetch details and state of a single post."""
        clean_id = post_id.replace("t3_", "")
        if subreddit:
            clean_sub = subreddit.strip().lstrip("r/").rstrip("/")
            path = f"/r/{clean_sub}/comments/{clean_id}.json"
        else:
            path = f"/comments/{clean_id}.json"

        data = await self._request("GET", path, params={"raw_json": 1})
        if not isinstance(data, list) or not data:
            raise RedditPostNotFoundError(f"Post {post_id} not found")

        post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
        if not post_data:
            raise RedditPostNotFoundError(f"Post {post_id} has no data")

        created_utc = post_data.get("created_utc", 0)
        return {
            "reddit_post_id": post_data.get("id"),
            "name": post_data.get("name"),
            "subreddit": post_data.get("subreddit"),
            "author": post_data.get("author"),
            "title": post_data.get("title", ""),
            "body": post_data.get("selftext", ""),
            "permalink": post_data.get("permalink", ""),
            "url": post_data.get("url", ""),
            "score": post_data.get("score", 0),
            "comment_count": post_data.get("num_comments", 0),
            "flair": post_data.get("link_flair_text"),
            "is_locked": post_data.get("locked", False),
            "is_archived": post_data.get("archived", False),
            "is_removed": post_data.get("removed_by_category") is not None,
            "created_at": datetime.fromtimestamp(created_utc, tz=timezone.utc),
        }

    async def fetch_comments(
        self,
        post_id: str,
        subreddit: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Fetch top comments for context."""
        clean_id = post_id.replace("t3_", "")
        if subreddit:
            clean_sub = subreddit.strip().lstrip("r/").rstrip("/")
            path = f"/r/{clean_sub}/comments/{clean_id}.json"
        else:
            path = f"/comments/{clean_id}.json"

        data = await self._request("GET", path, params={"limit": limit, "raw_json": 1})
        if not isinstance(data, list) or len(data) < 2:
            return []

        comment_children = data[1].get("data", {}).get("children", [])
        comments = []
        for child in comment_children:
            c = child.get("data", {})
            if "body" in c and c.get("body") != "[deleted]":
                comments.append({
                    "id": c.get("id"),
                    "author": c.get("author"),
                    "body": c.get("body"),
                    "score": c.get("score", 0),
                })
        return comments

    async def get_subreddit_info(self, subreddit: str) -> dict[str, Any]:
        """Fetch metadata for a subreddit."""
        clean_sub = subreddit.strip().lstrip("r/").rstrip("/")
        path = f"/r/{clean_sub}/about.json"
        data = await self._request("GET", path, params={"raw_json": 1})
        sub_data = data.get("data", {})
        return {
            "subreddit": clean_sub,
            "display_name": sub_data.get("display_name", clean_sub),
            "title": sub_data.get("title", ""),
            "description": sub_data.get("public_description", ""),
            "subscribers": sub_data.get("subscribers", 0),
            "over18": sub_data.get("over18", False),
            "submission_type": sub_data.get("submission_type", "any"),
        }

    async def get_community_rules(self, subreddit: str) -> dict[str, Any]:
        """Fetch official rules configured by subreddit moderators."""
        clean_sub = subreddit.strip().lstrip("r/").rstrip("/")
        path = f"/r/{clean_sub}/about/rules.json"
        data = await self._request("GET", path, params={"raw_json": 1})
        rules = data.get("rules", [])
        return {
            "subreddit": clean_sub,
            "rules": rules,
            "site_rules": data.get("site_rules", []),
        }

    async def submit_comment(self, post_id: str, body: str) -> dict[str, Any]:
        """
        Submit a comment to a Reddit post.
        Requires authenticated OAuth session with submit scope.
        """
        settings = get_settings()
        if not getattr(settings, "REDDIT_POSTING_ENABLED", False):
            raise RedditAuthError("Reddit posting is disabled by global safety policy.")

        if not self.is_oauth_configured:
            raise RedditAuthError("Reddit OAuth credentials are required to submit comments.")

        clean_id = post_id if post_id.startswith("t3_") else f"t3_{post_id}"
        path = "/api/comment"
        data = {
            "thing_id": clean_id,
            "text": body,
            "api_type": "json",
        }
        res = await self._request("POST", path, json_data=data)
        return res

    async def health_check(self) -> bool:
        """Verify reachability of Reddit discovery endpoint."""
        try:
            # Check a standard public endpoint
            data = await self._request("GET", "/r/technology/about.json")
            return bool(data.get("data", {}).get("display_name"))
        except Exception as exc:
            logger.debug("Reddit health check failed: %s", exc)
            return False
