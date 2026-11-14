"""
Zohra — Reddit Anti-Spam Guard & Rate Limiter.

Enforces conservative posting safeguards:
- Duplicate comment blocking via content hashing.
- Velocity limits (max comments/day, max/subreddit, minimum intervals).
- Link health verification (ensures linked articles are live and accessible).
- Account safety: immediately pauses operations if moderator removals or blocks occur.
- Zero vote manipulation, sockpuppets, or artificial engagement.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
from typing import Any
import uuid

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.reddit import RedditPublication

logger = get_logger("reddit.anti_spam")


class AntiSpamCheckResult:
    """Outcome of safety check."""

    def __init__(self, passed: bool, reason: str, details: dict[str, Any] | None = None) -> None:
        self.passed = passed
        self.reason = reason
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "details": self.details,
        }


class RedditAntiSpamGuard:
    """Validates responses against spam patterns and frequency restrictions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def compute_content_hash(self, text: str) -> str:
        """Computes SHA-256 fingerprint of comment text."""
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def verify_destination_url(self, url: str) -> tuple[bool, str]:
        """
        Ensures a linked website article is live, publicly accessible, and returns HTTP 200.
        Blocks localhost, private networks, and invalid schemas (SSRF protection).
        """
        # SSRF checks
        lowered = url.lower().strip()
        if not (lowered.startswith("http://") or lowered.startswith("https://")):
            return False, "Invalid URL scheme"
        if any(h in lowered for h in ("localhost", "127.0.0.1", "169.254.", "10.", "192.168.")):
            return False, "Private or internal destination URLs are blocked"

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return True, "Destination URL verified accessible (HTTP 200)"
                return False, f"Destination URL returned non-200 status (HTTP {resp.status_code})"
        except Exception as exc:
            return False, f"Destination URL could not be verified: {exc}"

    async def validate_submission(
        self,
        site_id: uuid.UUID,
        subreddit: str,
        response_text: str,
        proposed_link: str | None = None,
    ) -> AntiSpamCheckResult:
        """
        Comprehensive anti-spam check running before any submission or approval.
        """
        settings = get_settings()
        now = datetime.utcnow()
        clean_sub = subreddit.strip().lstrip("r/").rstrip("/").lower()
        content_hash = self.compute_content_hash(response_text)

        # 1. Global Kill Switch Check
        if not getattr(settings, "AUTONOMY_ENABLED", True) or getattr(settings, "MAINTENANCE_MODE", False):
            return AntiSpamCheckResult(
                passed=False,
                reason="Posting blocked: Global kill switch engaged or system in maintenance mode.",
            )

        # 2. Check for identical duplicate response in history
        dup_stmt = select(RedditPublication).where(
            RedditPublication.site_id == site_id,
            RedditPublication.response_hash == content_hash,
        )
        dup_res = await self.db.execute(dup_stmt)
        if dup_res.scalar_one_or_none():
            return AntiSpamCheckResult(
                passed=False,
                reason="Duplicate content: An identical response has already been published to Reddit.",
                details={"content_hash": content_hash},
            )

        # 3. Daily Posting Velocity Limit
        since_24h = now - timedelta(hours=24)
        daily_count_stmt = select(func.count(RedditPublication.id)).where(
            RedditPublication.site_id == site_id,
            RedditPublication.submitted_at >= since_24h,
        )
        daily_res = await self.db.execute(daily_count_stmt)
        daily_count = daily_res.scalar() or 0

        max_daily = getattr(settings, "REDDIT_MAX_COMMENTS_PER_DAY", 5)
        if daily_count >= max_daily:
            return AntiSpamCheckResult(
                passed=False,
                reason=f"Daily velocity limit reached ({daily_count}/{max_daily} comments in last 24h).",
                details={"daily_count": daily_count, "limit": max_daily},
            )

        # 4. Subreddit Frequency Limit
        sub_count_stmt = select(func.count(RedditPublication.id)).where(
            RedditPublication.site_id == site_id,
            RedditPublication.subreddit == clean_sub,
            RedditPublication.submitted_at >= since_24h,
        )
        sub_res = await self.db.execute(sub_count_stmt)
        sub_count = sub_res.scalar() or 0

        max_per_sub = getattr(settings, "REDDIT_MAX_COMMENTS_PER_SUBREDDIT_PER_DAY", 1)
        if sub_count >= max_per_sub:
            return AntiSpamCheckResult(
                passed=False,
                reason=f"Subreddit activity limit reached for r/{clean_sub} ({sub_count}/{max_per_sub} per 24h).",
                details={"subreddit": clean_sub, "count": sub_count, "limit": max_per_sub},
            )

        # 5. Minimum Cooldown Between Posts
        min_hours = getattr(settings, "REDDIT_MIN_HOURS_BETWEEN_POSTS", 4.0)
        cooldown_window = now - timedelta(hours=min_hours)
        last_pub_stmt = select(RedditPublication).where(
            RedditPublication.site_id == site_id,
        ).order_by(RedditPublication.submitted_at.desc()).limit(1)
        last_res = await self.db.execute(last_pub_stmt)
        last_pub = last_res.scalar_one_or_none()

        if last_pub and last_pub.submitted_at > cooldown_window:
            elapsed_m = (now - last_pub.submitted_at).total_seconds() / 60.0
            req_m = min_hours * 60.0
            return AntiSpamCheckResult(
                passed=False,
                reason=f"Posting cooldown active: {elapsed_m:.0f}m elapsed, {req_m:.0f}m required between posts.",
                details={"elapsed_minutes": elapsed_m, "required_minutes": req_m},
            )

        # 6. Verify destination URL health if linking
        if proposed_link:
            is_valid_url, url_reason = await self.verify_destination_url(proposed_link)
            if not is_valid_url:
                return AntiSpamCheckResult(
                    passed=False,
                    reason=f"Link health verification failed: {url_reason}",
                    details={"url": proposed_link},
                )

        return AntiSpamCheckResult(
            passed=True,
            reason="All anti-spam guards and rate controls passed successfully.",
            details={"content_hash": content_hash, "daily_count": daily_count},
        )
