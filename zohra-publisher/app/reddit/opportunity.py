"""
Zohra — Reddit Opportunity Scoring & Action Engine.

Scores content opportunities using multi-dimensional intelligence and determines
actionable editorial paths (CREATE_NEW_ARTICLE, UPDATE_EXISTING_ARTICLE, ADD_FAQ,
ANSWER_REDDIT_ONLY, WATCH, REJECT, HUMAN_REVIEW).
"""

from __future__ import annotations

import json
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.published_articles import PublishedArticle
from app.db.models.reddit import (
    RedditOpportunity,
    RedditOpportunityAction,
    RedditQuestion,
    RedditQuestionCluster,
)
from app.llm.base import LLMRequest, LLMRole
from app.llm.registry import get_default_provider
from app.reddit.dedup import RedditDuplicateDetector

logger = get_logger("reddit.opportunity")


class RedditOpportunityEngine:
    """Evaluates question opportunities and maps them to appropriate content actions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.dedup = RedditDuplicateDetector(db)

    async def evaluate_opportunity(
        self,
        site_id: uuid.UUID,
        question: RedditQuestion,
        cluster: RedditQuestionCluster | None = None,
    ) -> RedditOpportunity:
        """
        Analyzes a discovered question, checks existing site content for gaps,
        calculates opportunity scores, and assigns a concrete action.
        """
        reasons: list[str] = []

        # 1. Existing Content Match & Gap Analysis
        has_dup, matched_art, match_sim = await self.dedup.check_website_duplicate(
            site_id=site_id,
            question_text=question.primary_question,
            threshold=0.50,
        )

        content_gap_score = 90.0
        gap_summary = None
        if has_dup and matched_art is not None:
            reasons.append(f"Existing article match found: '{matched_art.title}' (similarity {match_sim:.2f})")
            if match_sim >= 0.75:
                content_gap_score = 30.0
                gap_summary = f"Existing article '{matched_art.title}' already extensively covers this core question."
            else:
                content_gap_score = 65.0
                gap_summary = f"Article '{matched_art.title}' exists, but this question addresses a distinct sub-angle or FAQ."
        else:
            reasons.append("No existing website content covers this specific problem (high content gap opportunity)")

        # 2. Recurrence Score (from cluster if available)
        recurrence_count = cluster.question_count if cluster else 1
        recurrence_score = min(100.0, 40.0 + (recurrence_count * 20.0))
        if recurrence_count > 1:
            reasons.append(f"Recurring community theme: {recurrence_count} related questions clustered")

        # 3. Component Scores
        web_relevance = question.relevance_score
        momentum = min(100.0, 30.0 + (question.reddit_score * 0.5) + (question.reddit_comment_count * 2.0))
        search_fit = 85.0 if question.search_intent in ("informational", "commercial") else 50.0
        evergreen = 80.0
        answerability = question.answerability_score

        # Synthesize Overall Opportunity Score
        overall = (
            (web_relevance * 0.30)
            + (content_gap_score * 0.25)
            + (recurrence_score * 0.15)
            + (search_fit * 0.15)
            + (momentum * 0.15)
        )
        overall_score = round(max(0.0, min(100.0, overall)), 2)
        confidence = 85.0

        # 4. Action Determination
        if has_dup and matched_art is not None:
            if match_sim >= 0.75:
                # Core topic is already well covered; can answer on Reddit or add FAQ
                recommended_action = RedditOpportunityAction.ANSWER_REDDIT_ONLY.value
                reasons.append("Action: Answer on Reddit using existing site knowledge rather than creating redundant article")
            elif match_sim >= 0.60:
                recommended_action = RedditOpportunityAction.ADD_FAQ.value
                reasons.append("Action: Recommend adding this specific user question to existing article FAQ section")
            else:
                recommended_action = RedditOpportunityAction.CREATE_SUPPORTING_ARTICLE.value
                reasons.append("Action: Recommend creating a supporting deep-dive linked to existing parent article")
        else:
            if overall_score >= 65.0:
                recommended_action = RedditOpportunityAction.CREATE_NEW_ARTICLE.value
                reasons.append("Action: High opportunity score and clear content gap justify standalone masterpiece article")
            elif overall_score >= 50.0:
                recommended_action = RedditOpportunityAction.WATCH.value
                reasons.append("Action: Moderate opportunity; place on watchlist for further community recurrence")
            else:
                recommended_action = RedditOpportunityAction.REJECT.value
                reasons.append("Action: Low opportunity score or insufficient relevance to core site themes")

        # 5. Editorial Title and Angle Synthesis
        title, angle, target_kw = self._synthesize_editorial_direction(question, cluster)

        opportunity = RedditOpportunity(
            site_id=site_id,
            question_id=question.id,
            cluster_id=cluster.id if cluster else None,
            working_title=title,
            proposed_angle=angle,
            target_keyword=target_kw,
            secondary_keywords=question.extracted_entities or [],
            recommended_action=recommended_action,
            existing_article_match_id=matched_art.id if matched_art else None,
            existing_article_title=matched_art.title if matched_art else None,
            content_gap_summary=gap_summary,
            website_relevance_score=web_relevance,
            recurrence_score=recurrence_score,
            engagement_momentum_score=momentum,
            content_gap_score=content_gap_score,
            search_intent_fit_score=search_fit,
            evergreen_score=evergreen,
            answerability_score=answerability,
            overall_opportunity_score=overall_score,
            confidence_score=confidence,
            score_reasons=reasons,
            handoff_status="ready_for_research" if recommended_action == RedditOpportunityAction.CREATE_NEW_ARTICLE.value else "complete",
            status="scored",
        )

        self.db.add(opportunity)
        await self.db.flush()
        await self.db.refresh(opportunity)
        return opportunity

    def _synthesize_editorial_direction(
        self,
        question: RedditQuestion,
        cluster: RedditQuestionCluster | None,
    ) -> tuple[str, str, str]:
        """Derives clean article title, strategic angle, and primary target keyword."""
        if cluster and cluster.parent_topic:
            title = cluster.parent_topic
            angle = f"Comprehensive first-principles guide solving: {cluster.canonical_problem}"
            target_kw = cluster.cluster_name
        else:
            q_text = question.primary_question.rstrip("?")
            title = f"{q_text}: The Comprehensive Practical Guide"
            angle = f"Actionable breakdown addressing the underlying challenge: {question.underlying_problem or q_text}"
            target_kw = question.extracted_entities[0] if question.extracted_entities else question.primary_question[:40]

        return title, angle, target_kw
