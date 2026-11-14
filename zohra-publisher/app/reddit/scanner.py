"""
Zohra — Reddit Question Scanner.

Monitors configured subreddits and search queries aligned with website topics.
Applies deterministic pre-filtering, LLM intent extraction, relevance scoring,
and duplicate protection before persisting qualified user questions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.reddit import RedditJobStatus, RedditQuestion, RedditSource
from app.reddit.classifier import RedditQuestionClassifier
from app.reddit.dedup import RedditDuplicateDetector
from app.reddit.provider import RedditProvider
from app.reddit.relevance import RedditRelevanceScorer

logger = get_logger("reddit.scanner")


class RedditQuestionScanner:
    """Discovers and ingests user questions from target subreddits."""

    def __init__(
        self,
        db: AsyncSession,
        provider: RedditProvider | None = None,
        site_topics: list[str] | None = None,
    ) -> None:
        self.db = db
        self.provider = provider or RedditProvider()
        self.classifier = RedditQuestionClassifier()
        self.relevance_scorer = RedditRelevanceScorer(site_topics=site_topics)
        self.dedup = RedditDuplicateDetector(db)

    async def scan_subreddit(
        self,
        site_id: uuid.UUID,
        subreddit: str,
        limit: int = 25,
        min_relevance: float = 50.0,
    ) -> list[RedditQuestion]:
        """
        Scans a subreddit for new, relevant user questions.
        """
        clean_sub = subreddit.strip().lstrip("r/").rstrip("/")
        logger.info("Scanning r/%s for questions (limit: %d)", clean_sub, limit)

        # 1. Fetch recent posts via official Reddit provider
        raw_posts = await self.provider.discover_posts(clean_sub, sort="new", limit=limit)

        discovered_questions: list[RedditQuestion] = []

        for p in raw_posts:
            title = p.get("title", "").strip()
            body = p.get("body", "").strip()
            post_id = p.get("reddit_post_id", "")

            if not title or not post_id:
                continue

            # 2. Fast deterministic pre-filter
            is_candidate, _ = self.classifier.fast_heuristic_check(title, body)
            if not is_candidate and not title.endswith("?"):
                continue

            # 3. Duplicate check against existing Reddit ingested questions
            is_dup, dup_reason = await self.dedup.check_reddit_duplicate(
                site_id=site_id,
                reddit_post_id=post_id,
                question_text=title,
            )
            if is_dup:
                logger.debug("Skipping duplicate Reddit post %s: %s", post_id, dup_reason)
                continue

            # 4. Deep Question Intent Analysis
            analysis = await self.classifier.analyze_question(title, body)
            if not analysis.is_question:
                continue

            # 5. Multi-dimensional Relevance Scoring
            relevance = self.relevance_scorer.calculate_relevance(
                question=analysis.primary_question,
                problem=analysis.underlying_problem,
                subreddit=clean_sub,
                score=p.get("score", 1),
                comment_count=p.get("comment_count", 0),
                posted_at=p.get("created_at"),
                extracted_entities=analysis.extracted_entities,
            )

            if relevance.overall_score < min_relevance:
                logger.debug("Question '%s' below relevance threshold (%.1f < %.1f)", title[:40], relevance.overall_score, min_relevance)
                continue

            # 6. Persist Discovered Question
            rq = RedditQuestion(
                site_id=site_id,
                reddit_post_id=post_id,
                subreddit=clean_sub,
                author_id=p.get("author"),
                permalink=p.get("permalink", ""),
                url=p.get("url", ""),
                raw_title=title,
                raw_body=body,
                flair=p.get("flair"),
                reddit_score=p.get("score", 1),
                reddit_comment_count=p.get("comment_count", 0),
                posted_at=p.get("created_at", datetime.utcnow()),
                is_question=True,
                question_type=analysis.question_type,
                primary_question=analysis.primary_question,
                underlying_problem=analysis.underlying_problem,
                search_intent=analysis.search_intent,
                target_audience=analysis.target_audience,
                extracted_entities=analysis.extracted_entities,
                urgency_level=analysis.urgency_level,
                relevance_score=relevance.overall_score,
                relevance_reasons=relevance.reasons,
                clarity_score=analysis.clarity_score,
                answerability_score=analysis.answerability_score,
                status=RedditJobStatus.DISCOVERED.value,
            )
            self.db.add(rq)
            discovered_questions.append(rq)

        await self.db.flush()
        logger.info("Found and saved %d new qualified questions from r/%s", len(discovered_questions), clean_sub)
        return discovered_questions

    async def scan_monitored_subreddits(
        self,
        site_id: uuid.UUID,
        subreddits: list[str] | None = None,
        limit_per_sub: int = 15,
    ) -> list[RedditQuestion]:
        """Scans all configured subreddits for the target site."""
        settings = get_settings()
        subs_to_scan = subreddits or getattr(settings, "REDDIT_MONITORED_SUBREDDITS", ["ChatGPT", "artificial"])

        all_discovered = []
        for sub in subs_to_scan:
            try:
                questions = await self.scan_subreddit(site_id=site_id, subreddit=sub, limit=limit_per_sub)
                all_discovered.extend(questions)
            except Exception as exc:
                logger.warning("Error scanning r/%s: %s", sub, exc)

        return all_discovered
