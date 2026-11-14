"""
Zohra — Reddit Learning Engine & Content Flywheel.

Feeds community engagement, referral performance, and article conversion data
back into Zohra's core optimization engine.

Strict Compliance Invariant:
The learning engine is hard-bounded never to learn deceptive behaviors:
- Never recommends increasing posting frequency beyond safe thresholds.
- Never suggests hiding affiliation or bypassing subreddit moderation.
- Never optimizes toward spam or artificial vote engagement.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.reddit import (
    RedditOpportunity,
    RedditPublication,
    RedditQuestionCluster,
    RedditReferralEvent,
)

logger = get_logger("reddit.learning")


class RedditLearningEngine:
    """Extracts strategic content intelligence from Reddit discoveries and referrals."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def evaluate_cluster_performance(self, site_id: uuid.UUID) -> list[dict[str, Any]]:
        """
        Identifies high-performing question clusters that generated active engagement
        and referral readers, providing high-leverage topics for evergreen guide expansion.
        """
        stmt = select(
            RedditQuestionCluster.id,
            RedditQuestionCluster.parent_topic,
            RedditQuestionCluster.question_count,
            RedditQuestionCluster.aggregate_momentum_score,
            func.count(RedditReferralEvent.id).label("total_referrals"),
        ).join(
            RedditOpportunity, RedditOpportunity.cluster_id == RedditQuestionCluster.id, isouter=True
        ).join(
            RedditReferralEvent, RedditReferralEvent.article_slug == RedditOpportunity.target_keyword, isouter=True
        ).where(
            RedditQuestionCluster.site_id == site_id,
        ).group_by(
            RedditQuestionCluster.id,
            RedditQuestionCluster.parent_topic,
            RedditQuestionCluster.question_count,
            RedditQuestionCluster.aggregate_momentum_score,
        ).order_by(
            func.count(RedditReferralEvent.id).desc(),
            RedditQuestionCluster.question_count.desc(),
        ).limit(20)

        res = await self.db.execute(stmt)
        insights = []
        for row in res.all():
            insights.append({
                "cluster_id": str(row[0]),
                "topic": row[1],
                "question_recurrence": row[2],
                "momentum_score": row[3],
                "referral_count": row[4] or 0,
                "recommended_action": "EXPAND_CLUSTER_GUIDE" if (row[2] >= 3 or (row[4] or 0) >= 5) else "MAINTAIN",
            })
        return insights

    async def extract_topic_expansion_candidates(self, site_id: uuid.UUID) -> list[dict[str, Any]]:
        """
        Detects recurring subquestions across active clusters that represent
        high-value opportunities for FAQ updates or supporting articles.
        """
        stmt = select(RedditOpportunity).where(
            RedditOpportunity.site_id == site_id,
            RedditOpportunity.recommended_action.in_(["update_existing_article", "add_faq", "create_supporting_article"]),
        ).order_by(RedditOpportunity.created_at.desc()).limit(20)

        res = await self.db.execute(stmt)
        candidates = []
        for opp in res.scalars().all():
            candidates.append({
                "opportunity_id": str(opp.id),
                "title": opp.working_title,
                "action": opp.recommended_action,
                "matched_article": opp.existing_article_title,
                "gap_summary": opp.content_gap_summary,
                "score": opp.overall_opportunity_score,
            })
        return candidates
