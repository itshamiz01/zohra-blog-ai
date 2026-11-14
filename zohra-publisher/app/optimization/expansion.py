"""
Zohra — Part 9 Query Expansion & Intent Realignment Engine.

Implements Sections 38 to 43 of Part 9 Master Prompt:
- Evaluates unexpected or rising search queries against core article intent
- Distinguishes whether to expand existing article vs recommend a standalone NEW ARTICLE
- Generates structured SectionExpansionPlans with research and verification requirements
- Protects against keyword stuffing and semantic dilution
"""

from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ExpansionDecisionType(str, Enum):
    EXPAND_SECTION = "EXPAND_SECTION"
    CREATE_NEW_ARTICLE = "CREATE_NEW_ARTICLE"
    REFOCUS_EXISTING = "REFOCUS_EXISTING"
    NO_ACTION_RELEVANCE_TOO_LOW = "NO_ACTION_RELEVANCE_TOO_LOW"


@dataclass
class SectionExpansionPlan:
    heading: str
    target_query: str
    intent: str
    questions_answered: list[str]
    required_research_topics: list[str]
    target_queries: list[str]
    estimated_word_range: tuple[int, int]
    suggested_internal_links: list[str]
    verification_requirements: list[str]
    semantic_similarity: float

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["estimated_word_range"] = list(self.estimated_word_range)
        return d


@dataclass
class QueryExpansionEvaluation:
    query: str
    impressions: int
    semantic_similarity: float
    decision: ExpansionDecisionType
    section_plan: SectionExpansionPlan | None = None
    reason: str = ""


class QueryExpansionEngine:
    """Decides how to capture rising search queries without harming existing content relevance."""

    @classmethod
    def evaluate_semantic_relevance(cls, query: str, article_topic: str, article_title: str) -> float:
        """
        Computes semantic similarity ratio between the emerging query and the article focus.
        """
        stopwords = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "with", "by", "from", "as", "into"}
        combined = f"{article_topic.lower()} {article_title.lower()}"

        q_words = {w for w in query.lower().split() if w not in stopwords} or set(query.lower().split())
        topic_words = {w for w in combined.split() if w not in stopwords} or set(combined.split())

        inter = q_words & topic_words
        overlap_q = len(inter) / max(1, len(q_words))
        overlap_t = len(inter) / max(1, len(topic_words))
        overlap = max(overlap_q, overlap_t * 0.8)

        seq_ratio = difflib.SequenceMatcher(None, query.lower(), article_title.lower()).ratio()
        entity_boost = 0.25 if inter else 0.0

        # Hybrid similarity score
        return round(min(1.0, (overlap * 0.5) + (seq_ratio * 0.25) + entity_boost), 2)

    @classmethod
    def evaluate_query_for_expansion(
        cls,
        rising_query: str,
        impressions: int,
        article_title: str,
        article_topic: str,
        article_body: str,
    ) -> QueryExpansionEvaluation:
        """
        Evaluates an emerging search query to decide between section expansion,
        creating a new article, or rejecting as keyword stuffing.
        """
        sim = cls.evaluate_semantic_relevance(rising_query, article_topic, article_title)
        query_in_body = rising_query.lower() in article_body.lower()

        # Case 1: Irrelevant query (impressions from broad match or ambiguity)
        if sim < 0.25:
            return QueryExpansionEvaluation(
                query=rising_query,
                impressions=impressions,
                semantic_similarity=sim,
                decision=ExpansionDecisionType.NO_ACTION_RELEVANCE_TOO_LOW,
                reason=f"Query '{rising_query}' has low semantic similarity ({sim:.2f}) to article topic. Rejecting to prevent keyword stuffing.",
            )

        # Case 2: Query represents a distinct substantial user intent (e.g. comparison, alternative, troubleshooting)
        # If impressions are high and intent is distinct -> create dedicated new article
        distinct_intent_keywords = ["vs", "versus", "alternative", "pricing", "cost", "login", "download", "tutorial"]
        has_distinct_intent = any(k in rising_query.lower() for k in distinct_intent_keywords)

        if has_distinct_intent and impressions >= 1000 and sim < 0.65:
            return QueryExpansionEvaluation(
                query=rising_query,
                impressions=impressions,
                semantic_similarity=sim,
                decision=ExpansionDecisionType.CREATE_NEW_ARTICLE,
                reason=(
                    f"Query '{rising_query}' exhibits high demand ({impressions} impr) and distinct user intent. "
                    f"Recommending Standalone new article instead of diluting current article."
                ),
            )

        # Case 3: Already answered in body
        if query_in_body and sim >= 0.50:
            return QueryExpansionEvaluation(
                query=rising_query,
                impressions=impressions,
                semantic_similarity=sim,
                decision=ExpansionDecisionType.REFOCUS_EXISTING,
                reason=f"Query '{rising_query}' is already present in article body. Consider elevating to a sub-heading (H3) for better snippet visibility.",
            )

        # Case 4: Strong natural expansion candidate
        heading_title = rising_query.title()
        if not heading_title.startswith(("How", "What", "Why", "When")):
            heading_title = f"Understanding {heading_title}"

        plan = SectionExpansionPlan(
            heading=heading_title,
            target_query=rising_query,
            intent="INFORMATIONAL",
            questions_answered=[f"What does {rising_query} mean in this context?", f"How does {rising_query} work?"],
            required_research_topics=[rising_query, f"{rising_query} best practices"],
            target_queries=[rising_query],
            estimated_word_range=(150, 300),
            suggested_internal_links=[],
            verification_requirements=["Fact-check all technical claims via Part 6", "Verify source provenance"],
            semantic_similarity=sim,
        )

        return QueryExpansionEvaluation(
            query=rising_query,
            impressions=impressions,
            semantic_similarity=sim,
            decision=ExpansionDecisionType.EXPAND_SECTION,
            section_plan=plan,
            reason=f"Query '{rising_query}' is a relevant subtopic ({sim:.2f} similarity) suitable for dedicated section expansion.",
        )
