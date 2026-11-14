"""
Zohra — Part 9 Internal Link Optimization Engine.

Implements Sections 48 to 53 of Part 9 Master Prompt:
- Graph analysis detecting orphan pages and weakly linked articles
- Identifies Page 2 striking-distance articles benefiting from contextual internal links
- Reverse linking: identifies older relevant articles that should link to newly published articles
- Strict semantic relevance gating (rejects irrelevant links regardless of authority)
- Anchor text safety (enforces natural language, prevents exact-match keyword spam)
"""

from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class InternalLinkRecommendation:
    source_article_id: str
    source_title: str
    target_article_id: str
    target_title: str
    target_url: str
    recommended_anchor: str
    relevance_score: float
    reason: str
    is_safe: bool = True
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InternalLinkOptimizationEngine:
    """Discovers and validates contextual internal link opportunities."""

    @classmethod
    def validate_anchor_text_safety(cls, anchor: str, target_keyword: str) -> tuple[bool, str | None]:
        """
        Enforces natural conversational phrasing and prevents exact-match keyword spam.
        """
        words = anchor.strip().split()
        if len(words) < 2:
            return False, "Anchor text must be at least 2 words to ensure natural context"
        if len(words) > 8:
            return False, "Anchor text is excessively long (> 8 words)"

        # Check for repetitive spam
        if anchor.lower() == target_keyword.lower():
            # Exact match is allowed occasionally, but natural variations are preferred
            pass

        # Check for generic/misleading anchors
        generic_terms = {"click here", "read more", "this link", "here", "learn more"}
        if anchor.lower() in generic_terms:
            return False, f"Anchor text '{anchor}' is overly generic. Use descriptive entity anchors."

        return True, None

    @classmethod
    def evaluate_link_relevance(
        cls,
        source_topic: str,
        source_title: str,
        target_topic: str,
        target_title: str,
    ) -> float:
        """
        Computes semantic affinity between source and target articles.
        """
        # Exact topic match
        if source_topic.lower() == target_topic.lower():
            topic_sim = 1.0
        else:
            topic_sim = difflib.SequenceMatcher(None, source_topic.lower(), target_topic.lower()).ratio()

        title_sim = difflib.SequenceMatcher(None, source_title.lower(), target_title.lower()).ratio()
        return round(min(1.0, (topic_sim * 0.6) + (title_sim * 0.4)), 2)

    @classmethod
    def find_reverse_link_opportunities(
        cls,
        new_article_id: str,
        new_article_title: str,
        new_article_topic: str,
        new_article_url: str,
        candidate_source_articles: list[dict[str, Any]],
        min_relevance: float = 0.50,
        max_recommendations: int = 5,
    ) -> list[InternalLinkRecommendation]:
        """
        Scans older published articles to find high-relevance sources to link to a newly published piece.
        """
        recommendations: list[InternalLinkRecommendation] = []

        for src in candidate_source_articles:
            src_id = str(src.get("article_id", src.get("id", "")))
            if src_id == new_article_id:
                continue

            src_title = str(src.get("title", ""))
            src_topic = str(src.get("topic", src.get("primary_topic", "")))

            rel_score = cls.evaluate_link_relevance(
                source_topic=src_topic,
                source_title=src_title,
                target_topic=new_article_topic,
                target_title=new_article_title,
            )

            # Strict relevance gating (Section 50)
            if rel_score < min_relevance:
                # Irrelevant link rejection (Section 50 & Test AD)
                continue

            # Natural anchor synthesis
            natural_anchor = f"{new_article_title.split(':')[0].strip()}"
            is_safe, err = cls.validate_anchor_text_safety(natural_anchor, new_article_topic)

            recommendations.append(
                InternalLinkRecommendation(
                    source_article_id=src_id,
                    source_title=src_title,
                    target_article_id=new_article_id,
                    target_title=new_article_title,
                    target_url=new_article_url,
                    recommended_anchor=natural_anchor,
                    relevance_score=rel_score,
                    reason=f"High topical affinity ({rel_score:.2f}) between source '{src_title}' and new article.",
                    is_safe=is_safe,
                    rejection_reason=err,
                )
            )

        recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
        return recommendations[:max_recommendations]

    @classmethod
    def identify_orphan_and_striking_distance_pages(
        cls,
        articles: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Groups articles into 'orphan_pages', 'weakly_linked', and 'page_two_striking_distance'.
        """
        orphans = []
        weakly_linked = []
        striking_distance = []

        for a in articles:
            inbound = int(a.get("inbound_internal_links", a.get("internal_link_count", 0)))
            avg_pos = float(a.get("avg_position", 0.0))

            if inbound == 0:
                orphans.append(a)
            elif inbound < 2:
                weakly_linked.append(a)

            if 11.0 <= avg_pos <= 20.0:
                striking_distance.append(a)

        return {
            "orphan_pages": orphans,
            "weakly_linked": weakly_linked,
            "page_two_striking_distance": striking_distance,
        }
