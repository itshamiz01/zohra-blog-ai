"""
Zohra — Cannibalization Detection & Content Action Recommendation Engine.

Prevents publishing duplicate articles targeting the same search intent.
Analyzes existing site content index to decide between:
CREATE (new distinct intent), UPDATE (existing article already targets this intent),
EXPAND (partial coverage needing section additions), MERGE, or REVIEW.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.constants import ContentAction, SearchIntent
from app.db.models.site_content import SiteContent


@dataclass
class CannibalizationCheckResult:
    recommended_action: ContentAction
    target_content_id: uuid.UUID | None
    cannibalization_risk_score: float  # 0 to 100
    matched_existing_url: str | None
    matched_existing_title: str | None
    similarity_score: float
    same_intent_detected: bool
    rationale: str
    existing_related_content: list[dict[str, Any]] = field(default_factory=list)


class CannibalizationDetector:
    """Detects content cannibalization risks against existing website pages."""

    def __init__(self, similarity_threshold: float = 0.70) -> None:
        self.similarity_threshold = similarity_threshold

    def calculate_token_similarity(self, s1: str, s2: str) -> float:
        """Calculates token similarity combining Jaccard and containment on content tokens."""
        stopwords = {"a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by"}
        w1 = {w for w in re.findall(r"\w+", s1.lower()) if w not in stopwords}
        w2 = {w for w in re.findall(r"\w+", s2.lower()) if w not in stopwords}
        if not w1 or not w2:
            w1 = set(re.findall(r"\w+", s1.lower()))
            w2 = set(re.findall(r"\w+", s2.lower()))
        if not w1 or not w2:
            return 0.0
        intersection = len(w1 & w2)
        jaccard = intersection / len(w1 | w2)
        containment = intersection / min(len(w1), len(w2))
        return max(jaccard, containment * 0.85)

    def evaluate(
        self,
        candidate_keyword: str,
        candidate_intent: SearchIntent,
        candidate_topic: str,
        existing_articles: list[SiteContent],
    ) -> CannibalizationCheckResult:
        if not existing_articles:
            return CannibalizationCheckResult(
                recommended_action=ContentAction.CREATE,
                target_content_id=None,
                cannibalization_risk_score=0.0,
                matched_existing_url=None,
                matched_existing_title=None,
                similarity_score=0.0,
                same_intent_detected=False,
                rationale="No existing site content in index; novel topic creation approved.",
            )

        best_match: SiteContent | None = None
        highest_sim = 0.0
        same_intent = False

        related_list: list[dict[str, Any]] = []

        q_clean = candidate_keyword.lower()

        for art in existing_articles:
            # Check title similarity
            title_sim = self.calculate_token_similarity(candidate_topic, art.title)
            # Check primary keyword similarity
            kw_sim = (
                self.calculate_token_similarity(q_clean, art.primary_keyword.lower())
                if art.primary_keyword
                else 0.0
            )

            # Combined content similarity
            sim = max(title_sim, kw_sim)

            # Intent comparison
            art_intent = art.primary_intent.lower() if art.primary_intent else "informational"
            intent_matches = (art_intent == candidate_intent.value.lower())

            if sim > 0.25:
                related_list.append({
                    "url": art.url,
                    "title": art.title,
                    "primary_keyword": art.primary_keyword,
                    "primary_intent": art.primary_intent,
                    "similarity": round(sim, 2),
                })

            if sim > highest_sim:
                highest_sim = sim
                best_match = art
                same_intent = intent_matches

        # Decision Matrix
        # Scenario E: High keyword/topic similarity AND identical search intent -> UPDATE
        if highest_sim >= self.similarity_threshold and same_intent:
            risk_score = min(95.0, 70.0 + (highest_sim * 25.0))
            return CannibalizationCheckResult(
                recommended_action=ContentAction.UPDATE,
                target_content_id=best_match.id if best_match else None,
                cannibalization_risk_score=round(risk_score, 1),
                matched_existing_url=best_match.url if best_match else None,
                matched_existing_title=best_match.title if best_match else None,
                similarity_score=round(highest_sim, 2),
                same_intent_detected=True,
                rationale=(
                    f"Existing article '{best_match.title if best_match else ''}' already targets "
                    f"identical intent '{candidate_intent.value}'. Recommending UPDATE to avoid cannibalization."
                ),
                existing_related_content=related_list[:3],
            )

        # Scenario F: Similar topic/entity, but DISTINCT search intent -> CREATE!
        # e.g. Existing = 'What is Model X' (informational), Candidate = 'How to use Model X' (tutorial)
        if highest_sim >= self.similarity_threshold and not same_intent:
            risk_score = 15.0  # Low cannibalization risk because intent is distinct
            return CannibalizationCheckResult(
                recommended_action=ContentAction.CREATE,
                target_content_id=None,
                cannibalization_risk_score=round(risk_score, 1),
                matched_existing_url=best_match.url if best_match else None,
                matched_existing_title=best_match.title if best_match else None,
                similarity_score=round(highest_sim, 2),
                same_intent_detected=False,
                rationale=(
                    f"Existing article '{best_match.title if best_match else ''}' covers this entity, "
                    f"but candidate targets distinct search intent ('{candidate_intent.value}' vs '{best_match.primary_intent if best_match else ''}'). "
                    f"Approved as complementary new article."
                ),
                existing_related_content=related_list[:3],
            )

        # Moderate similarity (0.45 to 0.70) with same intent -> EXPAND existing
        if highest_sim >= 0.45 and same_intent:
            risk_score = 45.0
            return CannibalizationCheckResult(
                recommended_action=ContentAction.EXPAND,
                target_content_id=best_match.id if best_match else None,
                cannibalization_risk_score=round(risk_score, 1),
                matched_existing_url=best_match.url if best_match else None,
                matched_existing_title=best_match.title if best_match else None,
                similarity_score=round(highest_sim, 2),
                same_intent_detected=True,
                rationale=(
                    f"Moderate overlap with '{best_match.title if best_match else ''}'. "
                    f"Recommend expanding existing page with this angle as a new comprehensive section."
                ),
                existing_related_content=related_list[:3],
            )

        # Low similarity -> Clean novel CREATE
        return CannibalizationCheckResult(
            recommended_action=ContentAction.CREATE,
            target_content_id=None,
            cannibalization_risk_score=round(highest_sim * 20.0, 1),
            matched_existing_url=None,
            matched_existing_title=None,
            similarity_score=round(highest_sim, 2),
            same_intent_detected=False,
            rationale="Topic and intent are distinct from all existing site content. CREATE approved.",
            existing_related_content=related_list[:3],
        )
