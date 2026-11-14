"""
Zohra — Reddit Opportunity & Referral Engine Master Service.

Orchestrates the complete lifecycle:
1. Reddit Question Discovery & Intent Analysis
2. Deduplication & Thematic Clustering
3. Opportunity Scoring & Action Resolution (CREATE / UPDATE / FAQ / ANSWER_ONLY / WATCH)
4. Handoff to Zohra Research & Editorial Engine
5. Useful Reddit Response Generation with Selective Linking
6. Subreddit Rule & Anti-Spam Verification
7. Operator Approval Gate
8. Idempotent Publication & Referral Attribution

Guiding Principle: Usefulness First — Not a Spam Bot.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.db.models.published_articles import PublishedArticle
from app.db.models.reddit import (
    RedditJobStatus,
    RedditOpportunity,
    RedditOpportunityAction,
    RedditPublication,
    RedditQuestion,
    RedditResponseDraft,
    RedditResponseType,
)
from app.reddit.anti_spam import RedditAntiSpamGuard
from app.reddit.approval import RedditApprovalManager
from app.reddit.clustering import RedditQuestionClusterer
from app.reddit.handoff import build_reddit_opportunity_package
from app.reddit.opportunity import RedditOpportunityEngine
from app.reddit.provider import RedditProvider
from app.reddit.referral import RedditReferralTracker, build_attributable_url
from app.reddit.response_writer import RedditResponseWriter
from app.reddit.rules import SubredditRuleChecker
from app.reddit.scanner import RedditQuestionScanner

logger = get_logger("reddit.service")


class RedditEngineService:
    """Master orchestrator for Reddit discovery, opportunity scoring, and response lifecycle."""

    def __init__(self, db: AsyncSession, provider: RedditProvider | None = None) -> None:
        self.db = db
        self.provider = provider or RedditProvider()
        self.scanner = RedditQuestionScanner(db, provider=self.provider)
        self.clusterer = RedditQuestionClusterer(db)
        self.opportunity_engine = RedditOpportunityEngine(db)
        self.rule_checker = SubredditRuleChecker(db, provider=self.provider)
        self.response_writer = RedditResponseWriter()
        self.anti_spam = RedditAntiSpamGuard(db)
        self.approval_mgr = RedditApprovalManager(db)
        self.referral_tracker = RedditReferralTracker(db)

    async def run_discovery_cycle(
        self,
        site_id: uuid.UUID,
        subreddits: list[str] | None = None,
        limit_per_sub: int = 15,
    ) -> list[RedditQuestion]:
        """Discovers, filters, and ingests fresh questions from Reddit."""
        settings = get_settings()
        if not getattr(settings, "REDDIT_DISCOVERY_ENABLED", True):
            logger.info("Reddit discovery is disabled in configuration.")
            return []

        return await self.scanner.scan_monitored_subreddits(
            site_id=site_id,
            subreddits=subreddits,
            limit_per_sub=limit_per_sub,
        )

    async def cluster_and_score_pending_questions(
        self,
        site_id: uuid.UUID,
        limit: int = 20,
    ) -> list[RedditOpportunity]:
        """
        Clusters newly discovered questions and evaluates them into content opportunities.
        """
        stmt = select(RedditQuestion).where(
            RedditQuestion.site_id == site_id,
            RedditQuestion.status == RedditJobStatus.DISCOVERED.value,
        ).order_by(RedditQuestion.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        questions = list(res.scalars().all())

        opportunities: list[RedditOpportunity] = []
        for q in questions:
            # 1. Cluster question
            cluster = await self.clusterer.assign_or_create_cluster(site_id, q)
            q.status = RedditJobStatus.CLUSTERED.value

            # 2. Opportunity scoring & action mapping
            opp = await self.opportunity_engine.evaluate_opportunity(site_id, q, cluster)
            q.status = RedditJobStatus.SCORED.value
            opportunities.append(opp)

        await self.db.flush()
        return opportunities

    async def draft_response_for_opportunity(
        self,
        site_id: uuid.UUID,
        opportunity: RedditOpportunity,
        article: PublishedArticle | None = None,
    ) -> RedditResponseDraft:
        """
        Drafts a high-value community answer, checks subreddit rules, evaluates
        anti-spam policies, and enqueues the draft into the approval queue.
        """
        question = opportunity.question
        if not question:
            stmt = select(RedditQuestion).where(RedditQuestion.id == opportunity.question_id)
            res = await self.db.execute(stmt)
            question = res.scalar_one_or_none()

        if not question:
            raise ZohraError("Cannot draft response without linked question", code="MISSING_QUESTION")

        # 1. Check Subreddit Community Rules
        policy = await self.rule_checker.get_or_refresh_policy(site_id, question.subreddit)
        is_link_allowed, link_rule_reason = self.rule_checker.check_link_permitted(policy)

        # 2. Check if destination article exists and can be linked
        target_article = article
        if not target_article and opportunity.existing_article_match_id:
            art_stmt = select(PublishedArticle).where(PublishedArticle.id == opportunity.existing_article_match_id)
            art_res = await self.db.execute(art_stmt)
            target_article = art_res.scalar_one_or_none()

        article_url = None
        allow_link = False

        if target_article and is_link_allowed:
            # Generate transparent attributable campaign URL
            raw_url = getattr(target_article, "url", f"https://example.com/articles/{target_article.slug}")
            article_url = build_attributable_url(raw_url, question.subreddit, campaign=f"reddit_{question.subreddit}")
            allow_link = True

        # 3. Generate Authentic Standalone Reddit Answer
        generated = await self.response_writer.generate_response(
            question_title=question.primary_question,
            question_body=question.raw_body,
            article_title=target_article.title if target_article else None,
            article_url=article_url if allow_link else None,
            article_excerpt=getattr(target_article, "excerpt", None) if target_article else None,
            allow_link=allow_link,
        )

        # 4. Anti-Spam Guard Check
        anti_spam_res = await self.anti_spam.validate_submission(
            site_id=site_id,
            subreddit=question.subreddit,
            response_text=generated.full_markdown,
            proposed_link=generated.included_link,
        )

        # 5. Persist Draft in Approval Queue
        draft = RedditResponseDraft(
            site_id=site_id,
            opportunity_id=opportunity.id,
            reddit_post_id=question.reddit_post_id,
            subreddit=question.subreddit,
            response_type=generated.response_type,
            response_body=generated.full_markdown,
            has_external_link=bool(generated.included_link),
            proposed_link=generated.included_link,
            link_rationale=generated.link_rationale or link_rule_reason,
            rule_check_passed=is_link_allowed if generated.included_link else True,
            rule_check_details={"policy_status": policy.rule_status, "reason": link_rule_reason},
            anti_spam_passed=anti_spam_res.passed,
            anti_spam_details=anti_spam_res.to_dict(),
            destination_article_verified=bool(article_url),
            status=RedditJobStatus.AWAITING_APPROVAL.value,
        )
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)

        logger.info("Draft response %s created for post %s (status: awaiting_approval)", draft.id, question.reddit_post_id)
        return draft

    async def execute_dry_run(
        self,
        site_id: uuid.UUID,
        sample_title: str,
        sample_body: str | None = None,
        subreddit: str = "education",
    ) -> dict[str, Any]:
        """
        Executes a complete dry-run simulation without submitting anything to Reddit.
        """
        # Step 1: Classification & Intent
        analysis = await self.scanner.classifier.analyze_question(sample_title, sample_body)

        # Step 2: Relevance
        relevance = self.scanner.relevance_scorer.calculate_relevance(
            question=analysis.primary_question,
            problem=analysis.underlying_problem,
            subreddit=subreddit,
        )

        # Step 3: Duplicate & Website Check
        has_dup, matched_art, match_sim = await self.opportunity_engine.dedup.check_website_duplicate(
            site_id=site_id,
            question_text=analysis.primary_question,
        )

        # Step 4: Action & Editorial Angle
        overall_score = round((relevance.overall_score * 0.5) + (75.0 * 0.5), 1)
        if has_dup and matched_art:
            action = RedditOpportunityAction.ANSWER_REDDIT_ONLY.value
            proposed_article = matched_art.title
            art_status = "already_published"
        else:
            action = RedditOpportunityAction.CREATE_NEW_ARTICLE.value
            proposed_article = f"{analysis.primary_question.rstrip('?')}: The Definitive Guide"
            art_status = "ready_for_research"

        # Step 5: Rules Check
        policy = await self.rule_checker.get_or_refresh_policy(site_id, subreddit)
        links_allowed, rule_reason = self.rule_checker.check_link_permitted(policy)

        # Step 6: Generate Sample Response
        sample_url = f"https://example.com/articles/guide-{subreddit}" if links_allowed else None
        generated = await self.response_writer.generate_response(
            question_title=analysis.primary_question,
            question_body=sample_body,
            article_title=proposed_article,
            article_url=sample_url,
            allow_link=links_allowed,
        )

        # Step 7: Anti-Spam Check
        anti_spam_res = await self.anti_spam.validate_submission(
            site_id=site_id,
            subreddit=subreddit,
            response_text=generated.full_markdown,
            proposed_link=generated.included_link,
        )

        settings = get_settings()
        posting_enabled = getattr(settings, "REDDIT_POSTING_ENABLED", False)

        return {
            "question_detected": analysis.primary_question,
            "question_type": analysis.question_type,
            "why_selected": relevance.reasons,
            "relevance_score": relevance.overall_score,
            "opportunity_score": overall_score,
            "recommended_website_action": action,
            "proposed_article": proposed_article,
            "research_status": "handoff_ready",
            "article_status": art_status,
            "proposed_reddit_answer": generated.answer_text,
            "would_include_link": bool(generated.included_link),
            "link_inclusion_reason": generated.link_rationale or rule_reason,
            "community_rule_result": {
                "rule_status": policy.rule_status,
                "external_links_allowed": policy.external_links_allowed,
                "explanation": rule_reason,
            },
            "anti_spam_result": anti_spam_res.to_dict(),
            "would_publish": False,  # Dry run NEVER posts
            "posting_gate_status": "POSTING_DISABLED" if not posting_enabled else "APPROVAL_REQUIRED",
        }
