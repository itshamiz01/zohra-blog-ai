"""
Zohra — Reddit Referral Tracking & Attribution Engine.

Generates transparent UTM tracking URLs and maintains end-to-end attribution:
Reddit Question -> Opportunity -> Article -> Response -> Referral -> Session.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.reddit import RedditPublication, RedditReferralEvent

logger = get_logger("reddit.referral")


def build_attributable_url(
    base_url: str,
    subreddit: str,
    campaign: str | None = None,
) -> str:
    """
    Appends standard, non-invasive UTM tracking parameters for transparent attribution.
    Example: https://example.com/article-slug?utm_source=reddit&utm_medium=community&utm_campaign=r_education
    """
    clean_sub = subreddit.strip().lstrip("r/").rstrip("/").lower()
    parsed = urlparse(base_url)
    query_params = parse_qs(parsed.query)

    query_params["utm_source"] = ["reddit"]
    query_params["utm_medium"] = ["community"]
    query_params["utm_campaign"] = [campaign or f"r_{clean_sub}"]

    new_query = urlencode(query_params, doseq=True)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))


class RedditReferralTracker:
    """Records and aggregates referral metrics originating from Reddit community answers."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_referral(
        self,
        site_id: uuid.UUID,
        destination_url: str,
        article_slug: str,
        subreddit: str,
        utm_campaign: str,
        session_id: str | None = None,
        publication_id: uuid.UUID | None = None,
        engaged_seconds: float = 0.0,
        converted: bool = False,
    ) -> RedditReferralEvent:
        """Records an incoming referral click originating from Reddit."""
        event = RedditReferralEvent(
            site_id=site_id,
            publication_id=publication_id,
            subreddit=subreddit.strip().lstrip("r/").rstrip("/").lower(),
            destination_url=destination_url,
            article_slug=article_slug,
            utm_source="reddit",
            utm_medium="community",
            utm_campaign=utm_campaign,
            session_id=session_id,
            pageviews=1,
            engaged_seconds=engaged_seconds,
            converted=converted,
            occurred_at=datetime.utcnow(),
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_referral_summary(self, site_id: uuid.UUID, days: int = 30) -> dict[str, Any]:
        """Calculates referral performance over the specified time window."""
        since = datetime.utcnow() - timedelta(days=days)

        # Total referral sessions and pageviews
        stmt = select(
            func.count(RedditReferralEvent.id).label("total_referrals"),
            func.sum(RedditReferralEvent.pageviews).label("total_pageviews"),
            func.sum(RedditReferralEvent.engaged_seconds).label("total_engaged_seconds"),
        ).where(
            RedditReferralEvent.site_id == site_id,
            RedditReferralEvent.occurred_at >= since,
        )
        res = await self.db.execute(stmt)
        row = res.one_or_none()

        total_refs = row.total_referrals if row and row.total_referrals else 0
        total_pvs = row.total_pageviews if row and row.total_pageviews else 0
        total_sec = row.total_engaged_seconds if row and row.total_engaged_seconds else 0.0

        # Referrals by Subreddit
        sub_stmt = select(
            RedditReferralEvent.subreddit,
            func.count(RedditReferralEvent.id).label("count"),
        ).where(
            RedditReferralEvent.site_id == site_id,
            RedditReferralEvent.occurred_at >= since,
        ).group_by(RedditReferralEvent.subreddit).order_by(func.count(RedditReferralEvent.id).desc()).limit(10)
        sub_res = await self.db.execute(sub_stmt)
        by_subreddit = [{"subreddit": r[0], "referrals": r[1]} for r in sub_res.all()]

        return {
            "period_days": days,
            "total_referrals": total_refs,
            "total_pageviews": total_pvs,
            "avg_engaged_seconds": round(total_sec / max(total_refs, 1), 1),
            "by_subreddit": by_subreddit,
        }
