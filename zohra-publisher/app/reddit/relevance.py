"""
Zohra — Reddit Relevance Scorer.

Calculates multi-dimensional relevance between Reddit questions and website niches.
Stores all component scores and explicit rationale — no unexplained magic numbers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from pydantic import BaseModel, Field


class RelevanceScoreResult(BaseModel):
    """Multi-dimensional relevance evaluation output."""

    overall_score: float = Field(description="Synthesized relevance score from 0.0 to 100.0")
    topical_relevance_score: float
    audience_fit_score: float
    clarity_score: float
    answerability_score: float
    freshness_score: float
    momentum_score: float
    search_potential_score: float
    long_term_value_score: float
    reasons: list[str] = Field(default_factory=list, description="Detailed explanation of scores")


class RedditRelevanceScorer:
    """Evaluates question alignment with target site topics, audiences, and search demand."""

    def __init__(self, site_topics: list[str] | None = None) -> None:
        self.site_topics = [t.lower().strip() for t in (site_topics or [
            "ai in education",
            "chatgpt study techniques",
            "ai tools for students",
            "academic integrity",
            "critical thinking",
            "personalized learning",
            "ethical ai",
            "future of work and skills",
            "stem learning",
            "machine learning tutorials",
        ])]

    def calculate_relevance(
        self,
        question: str,
        problem: str | None,
        subreddit: str,
        score: int = 1,
        comment_count: int = 0,
        posted_at: datetime | None = None,
        extracted_entities: list[str] | None = None,
    ) -> RelevanceScoreResult:
        """
        Computes transparent multi-dimensional relevance scores.
        """
        reasons: list[str] = []
        text = f"{question} {problem or ''} {' '.join(extracted_entities or [])}".lower()

        # 1. Topical Relevance
        matched_topics = [t for t in self.site_topics if t in text or any(w in text for w in t.split())]
        topic_match_ratio = len(matched_topics) / max(len(self.site_topics), 1)

        # Baseline check on core keywords
        core_stems = ("ai", "chatgpt", "learn", "study", "student", "school", "exam", "teach", "skill", "code", "guide")
        stem_matches = sum(1 for s in core_stems if s in text)

        topical_score = min(100.0, (len(matched_topics) * 25.0) + (stem_matches * 8.0))
        if topical_score >= 60.0:
            reasons.append(f"Strong topical overlap with site themes ({', '.join(matched_topics[:3])})")
        else:
            reasons.append("Moderate topical alignment with educational and AI themes")

        # 2. Audience Fit
        audience_keywords = ("student", "beginner", "teacher", "learner", "self-taught", "developer", "educator", "college", "class")
        aud_matches = sum(1 for a in audience_keywords if a in text)
        audience_score = min(100.0, 50.0 + (aud_matches * 15.0))
        if aud_matches > 0:
            reasons.append("Directly targets core audience persona (learners, educators, practitioners)")

        # 3. Clarity Score
        length = len(question.split())
        if 6 <= length <= 25:
            clarity_score = 90.0
            reasons.append("Well-formed and specific query length")
        elif length < 6:
            clarity_score = 45.0
            reasons.append("Very short question; potential ambiguity")
        else:
            clarity_score = 75.0

        # 4. Answerability Score
        # Direct questions with problem statements are highly answerable with actionable guides
        answerability_score = 80.0
        if any(w in text for w in ("how to", "best way", "difference between", "step by step")):
            answerability_score = 95.0
            reasons.append("Structured 'how-to' or comparative query with high guide answerability")

        # 5. Freshness Score
        now = datetime.now(timezone.utc)
        if posted_at:
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
            hours_old = max(0.0, (now - posted_at).total_seconds() / 3600.0)
            if hours_old < 24.0:
                freshness_score = 95.0
                reasons.append(f"Recent discussion ({hours_old:.1f} hours old)")
            elif hours_old < 72.0:
                freshness_score = 75.0
            elif hours_old < 168.0:
                freshness_score = 60.0
            else:
                freshness_score = 40.0
        else:
            freshness_score = 70.0

        # 6. Momentum Score (upvotes & discussion activity)
        momentum_score = min(100.0, 30.0 + (score * 0.5) + (comment_count * 2.0))
        if comment_count > 10:
            reasons.append(f"Active community engagement ({comment_count} comments)")

        # 7. Search Potential
        # Questions with high information need make excellent evergreen search articles
        search_indicators = ("how to", "best", "guide", "tutorial", "difference", "can", "why")
        search_matches = sum(1 for ind in search_indicators if ind in text)
        search_potential_score = min(100.0, 50.0 + (search_matches * 15.0))

        # 8. Long-term / Evergreen Value
        time_sensitive_words = ("today", "yesterday", "breaking", "update 2.1", "outage", "down right now")
        is_fleeting = any(w in text for w in time_sensitive_words)
        if is_fleeting:
            long_term_value_score = 30.0
            reasons.append("Time-sensitive or transient issue")
        else:
            long_term_value_score = 85.0
            reasons.append("Evergreen educational/practical value")

        # Synthesize Overall Score
        overall = (
            (topical_score * 0.30)
            + (audience_score * 0.15)
            + (clarity_score * 0.10)
            + (answerability_score * 0.15)
            + (search_potential_score * 0.15)
            + (long_term_value_score * 0.15)
        )
        overall_score = round(max(0.0, min(100.0, overall)), 2)

        return RelevanceScoreResult(
            overall_score=overall_score,
            topical_relevance_score=round(topical_score, 1),
            audience_fit_score=round(audience_score, 1),
            clarity_score=round(clarity_score, 1),
            answerability_score=round(answerability_score, 1),
            freshness_score=round(freshness_score, 1),
            momentum_score=round(momentum_score, 1),
            search_potential_score=round(search_potential_score, 1),
            long_term_value_score=round(long_term_value_score, 1),
            reasons=reasons,
        )
