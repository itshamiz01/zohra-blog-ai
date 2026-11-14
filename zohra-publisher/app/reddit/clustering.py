"""
Zohra — Reddit Question Clustering Engine.

Clusters related Reddit questions into comprehensive parent topics and subtopics
rather than generating fragmented, low-substance standalone articles.
"""

from __future__ import annotations

import json
import re
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.reddit import RedditQuestion, RedditQuestionCluster
from app.llm.base import LLMRequest, LLMRole
from app.llm.registry import get_default_provider
from app.reddit.dedup import calculate_jaccard_similarity

logger = get_logger("reddit.clustering")


class RedditQuestionClusterer:
    """Assigns questions to existing topic clusters or synthesizes new strategic clusters."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def assign_or_create_cluster(
        self,
        site_id: uuid.UUID,
        question: RedditQuestion,
    ) -> RedditQuestionCluster:
        """
        Evaluates question against existing active clusters. If a strong thematic match exists,
        assigns it to the cluster. Otherwise, synthesizes a new cluster.
        """
        # Fetch active clusters for site
        stmt = select(RedditQuestionCluster).where(
            RedditQuestionCluster.site_id == site_id,
            RedditQuestionCluster.is_active.is_(True),
        ).limit(50)
        res = await self.db.execute(stmt)
        clusters = res.scalars().all()

        best_cluster = None
        highest_sim = 0.0

        for cl in clusters:
            sim = calculate_jaccard_similarity(question.primary_question, cl.parent_topic)
            prob_sim = calculate_jaccard_similarity(question.underlying_problem or "", cl.canonical_problem)
            combined_sim = (sim * 0.6) + (prob_sim * 0.4)

            if combined_sim > highest_sim:
                highest_sim = combined_sim
                best_cluster = cl

        # If similarity exceeds threshold, attach to existing cluster
        if highest_sim >= 0.45 and best_cluster is not None:
            best_cluster.question_count += 1
            best_cluster.aggregate_momentum_score = min(
                100.0, best_cluster.aggregate_momentum_score + (question.relevance_score * 0.1)
            )
            question.cluster_id = best_cluster.id
            await self.db.flush()
            logger.info(
                "Assigned question '%s' to cluster '%s' (similarity: %.2f)",
                question.primary_question[:40], best_cluster.parent_topic, highest_sim
            )
            return best_cluster

        # Synthesize a new cluster using LLM
        cluster_data = await self._synthesize_cluster_meta(question.primary_question, question.underlying_problem)

        new_cluster = RedditQuestionCluster(
            site_id=site_id,
            cluster_name=cluster_data["cluster_name"],
            parent_topic=cluster_data["parent_topic"],
            canonical_problem=cluster_data["canonical_problem"],
            subtopics=cluster_data["subtopics"],
            question_count=1,
            primary_intent=question.search_intent or "informational",
            aggregate_momentum_score=max(50.0, float(question.relevance_score or 50.0)),
            is_active=True,
        )
        self.db.add(new_cluster)
        await self.db.flush()
        await self.db.refresh(new_cluster)

        question.cluster_id = new_cluster.id
        await self.db.flush()
        logger.info("Created new cluster '%s' for question", new_cluster.parent_topic)
        return new_cluster

    async def _synthesize_cluster_meta(self, question: str, problem: str | None) -> dict[str, Any]:
        """Synthesizes parent topic, core problem, and subtopics from question."""
        prompt = f"""
Given this real user question from Reddit:
QUESTION: "{question}"
CONTEXT / PROBLEM: "{problem or question}"

Create an authoritative parent topic cluster for a high-quality educational website.
Do not make it narrow to one person's situation. Group the broader thematic space.

Respond strictly in JSON format:
{{
  "cluster_name": "Short identifier e.g. Responsible AI for Students",
  "parent_topic": "Broad Parent Topic Title e.g. How Students Can Use AI Without Becoming Dependent on It",
  "canonical_problem": "The systemic or learning dilemma facing the user",
  "subtopics": [
    "AI and critical thinking",
    "Academic integrity boundaries",
    "Prompt engineering for study workflows",
    "Self-testing strategies with LLMs"
  ]
}}
"""
        provider = get_default_provider()
        req = LLMRequest(
            prompt=prompt,
            role=LLMRole.RESEARCH,
            temperature=0.3,
            max_tokens=400,
            response_format={"type": "json_object"},
        )

        try:
            resp = await provider.generate(req)
            data = json.loads(resp.content.strip())
            return {
                "cluster_name": str(data.get("cluster_name") or question[:40]),
                "parent_topic": str(data.get("parent_topic") or question),
                "canonical_problem": str(data.get("canonical_problem") or (problem or question)),
                "subtopics": list(data.get("subtopics") or ["Overview", "Key Strategies", "FAQ"]),
            }
        except Exception as exc:
            logger.warning("Cluster synthesis fallback: %s", exc)

        return {
            "cluster_name": question[:50],
            "parent_topic": question,
            "canonical_problem": problem or question,
            "subtopics": ["Understanding the Problem", "Step-by-Step Solutions", "Best Practices"],
        }
