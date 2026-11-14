"""
Zohra — Reddit Duplicate & Overlap Detector.

Performs three-tier deduplication:
1. Reddit duplicates (same post or identical recent Reddit question)
2. Website duplicates (existing published articles covering the topic)
3. Pipeline duplicates (opportunities already actively being researched or written)
"""

from __future__ import annotations

import re
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.published_articles import PublishedArticle
from app.db.models.reddit import RedditOpportunity, RedditQuestion


def normalize_text_for_similarity(text: str) -> str:
    """Normalize text for token-based comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [w for w in text.split() if len(w) > 2 and w not in ("the", "and", "for", "with", "this", "that")]
    return " ".join(sorted(set(tokens)))


def calculate_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Calculate token Jaccard similarity between two strings."""
    tokens_a = set(normalize_text_for_similarity(text_a).split())
    tokens_b = set(normalize_text_for_similarity(text_b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


class RedditDuplicateDetector:
    """Detects duplicates across Reddit ingest, published content, and pipeline jobs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_reddit_duplicate(
        self,
        site_id: uuid.UUID,
        reddit_post_id: str,
        question_text: str,
    ) -> tuple[bool, str | None]:
        """Check if post is already ingested or near-identical to recent Reddit question."""
        # 1. Exact post ID check
        stmt = select(RedditQuestion).where(
            RedditQuestion.site_id == site_id,
            RedditQuestion.reddit_post_id == reddit_post_id,
        )
        res = await self.db.execute(stmt)
        if res.scalar_one_or_none():
            return True, f"Exact Reddit post {reddit_post_id} already ingested"

        # 2. Semantic/token similarity check against recent questions
        recent_stmt = select(RedditQuestion).where(
            RedditQuestion.site_id == site_id
        ).order_by(RedditQuestion.created_at.desc()).limit(100)
        recent_res = await self.db.execute(recent_stmt)
        recent_questions = recent_res.scalars().all()

        for rq in recent_questions:
            sim = calculate_jaccard_similarity(question_text, rq.primary_question)
            if sim >= 0.85:
                return True, f"Near-duplicate of existing Reddit question '{rq.primary_question[:60]}' (similarity {sim:.2f})"

        return False, None

    async def check_website_duplicate(
        self,
        site_id: uuid.UUID,
        question_text: str,
        threshold: float = 0.55,
    ) -> tuple[bool, PublishedArticle | None, float]:
        """
        Check if an existing published website article already comprehensively answers this question.
        Returns (is_duplicate, matched_article, similarity_score).
        """
        stmt = select(PublishedArticle).where(
            PublishedArticle.site_id == site_id,
            PublishedArticle.status == "published",
        ).order_by(PublishedArticle.created_at.desc()).limit(200)
        res = await self.db.execute(stmt)
        articles = res.scalars().all()

        best_match = None
        highest_sim = 0.0

        for art in articles:
            sim = calculate_jaccard_similarity(question_text, art.title)
            if sim > highest_sim:
                highest_sim = sim
                best_match = art

        if highest_sim >= threshold and best_match is not None:
            return True, best_match, round(highest_sim, 2)

        return False, None, round(highest_sim, 2)

    async def check_pipeline_duplicate(
        self,
        site_id: uuid.UUID,
        topic: str,
    ) -> bool:
        """Check if an active opportunity or draft is already in progress for this topic."""
        stmt = select(RedditOpportunity).where(
            RedditOpportunity.site_id == site_id,
            RedditOpportunity.status.in_(["researching", "article_creating", "ready_for_research"]),
        )
        res = await self.db.execute(stmt)
        active_opps = res.scalars().all()

        for opp in active_opps:
            if calculate_jaccard_similarity(topic, opp.working_title) >= 0.70:
                return True

        return False
