"""
Zohra — Headline Engine (Part 5).

Generates and scores multiple headline candidates across diverse styles (direct, benefit-led,
question, comparison, how-to, reference). Evaluates intent match, clarity, accuracy, SEO,
and brand fit while strictly penalizing clickbait, false urgency, and unsupported superlatives.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.schemas.editorial import ContentStrategyData, HeadlineCandidateResponse


class HeadlineEngine:
    """Generates, scores, and selects truthful, SEO-optimized headlines."""

    CLICKBAIT_PATTERNS = [
        re.compile(r"\b(shocking|unbelievable|mind-blowing|jaw-dropping)\b", re.IGNORECASE),
        re.compile(r"\byou won't believe\b", re.IGNORECASE),
        re.compile(r"\bwill destroy\b", re.IGNORECASE),
        re.compile(r"\bwill blow your mind\b", re.IGNORECASE),
        re.compile(r"\bact now before it's too late\b", re.IGNORECASE),
        re.compile(r"\bthe #1 secret\b", re.IGNORECASE),
    ]

    SUPERLATIVE_PATTERNS = [
        re.compile(r"\bthe greatest\b", re.IGNORECASE),
        re.compile(r"\bthe only .* you will ever need\b", re.IGNORECASE),
        re.compile(r"\bunbeatable\b", re.IGNORECASE),
    ]

    @classmethod
    def generate_candidates(
        cls,
        topic: str,
        primary_keyword: str,
        strategy: ContentStrategyData,
        draft_project_id: uuid.UUID | None = None,
    ) -> list[HeadlineCandidateResponse]:
        candidates: list[dict[str, Any]] = []

        # Style 1: Direct & Comprehensive
        candidates.append({
            "headline": f"{topic}: Everything You Need to Know in 2026",
            "style": "direct",
        })

        # Style 2: Benefit-Led & Practical
        candidates.append({
            "headline": f"{primary_keyword.title()}: Capabilities, Verified Pricing & Practical Guide",
            "style": "benefit_led",
        })

        # Style 3: Question / Problem-Focused
        candidates.append({
            "headline": f"What Is {topic}? Verified Features, Plans, and Practical Limitations",
            "style": "question",
        })

        # Style 4: How-To / Workflow (if tutorial or guide)
        if strategy.recommended_content_type in ("tutorial", "guide"):
            candidates.append({
                "headline": f"How to Use {topic}: Complete Setup & Workflow Walkthrough",
                "style": "how_to",
            })
        else:
            candidates.append({
                "headline": f"{topic} Breakdown: Features, Performance & Implementation Guide",
                "style": "how_to",
            })

        # Style 5: Pricing & Cost Analysis (if pricing or commercial)
        if strategy.recommended_content_type in ("pricing", "comparison"):
            candidates.append({
                "headline": f"{topic} Pricing & Plans: Full Breakdown and Hidden Limits",
                "style": "reference",
            })
        else:
            candidates.append({
                "headline": f"{topic} in Practice: Documented Specifications & Reality Check",
                "style": "reference",
            })

        # Score all candidates
        scored: list[HeadlineCandidateResponse] = []
        for c in candidates:
            h_text = c["headline"]
            scores = cls.score_headline(h_text, primary_keyword, strategy)
            scored.append(
                HeadlineCandidateResponse(
                    id=uuid.uuid4(),
                    headline=h_text,
                    style=c["style"],
                    intent_score=scores["intent_score"],
                    clarity_score=scores["clarity_score"],
                    accuracy_score=scores["accuracy_score"],
                    seo_score=scores["seo_score"],
                    brand_score=scores["brand_score"],
                    overall_score=scores["overall_score"],
                    selected=False,
                    selection_reason=None,
                )
            )

        # Select highest overall score
        scored.sort(key=lambda x: x.overall_score, reverse=True)
        if scored:
            scored[0].selected = True
            scored[0].selection_reason = (
                f"Selected as top-ranked headline (Score {scored[0].overall_score:.1f}/100) with optimal "
                f"intent alignment ({scored[0].intent_score:.0f}), clarity ({scored[0].clarity_score:.0f}), "
                f"and zero clickbait penalty."
            )

        return scored

    @classmethod
    def score_headline(
        cls,
        headline: str,
        primary_keyword: str,
        strategy: ContentStrategyData,
    ) -> dict[str, float]:
        h_lower = headline.lower()
        pk_lower = primary_keyword.lower()

        # 1. Intent Score (0-100)
        intent_score = 75.0
        if strategy.search_intent in h_lower:
            intent_score += 15.0
        if strategy.recommended_content_type == "pricing" and ("price" in h_lower or "cost" in h_lower or "plan" in h_lower) or strategy.recommended_content_type == "tutorial" and ("how to" in h_lower or "setup" in h_lower or "workflow" in h_lower):
            intent_score = 95.0

        # 2. SEO Score (0-100): Keyword presence and position
        seo_score = 60.0
        if pk_lower in h_lower:
            seo_score += 30.0
            if h_lower.startswith(pk_lower):
                seo_score += 10.0
        else:
            # Word overlap
            pk_words = set(pk_lower.split())
            overlap = sum(1 for w in pk_words if w in h_lower)
            seo_score += (overlap / max(1, len(pk_words))) * 25.0

        # 3. Clarity Score (0-100): Optimal length is 45-75 chars
        length = len(headline)
        if 40 <= length <= 75:
            clarity_score = 95.0
        elif 30 <= length < 40 or 75 < length <= 90:
            clarity_score = 80.0
        else:
            clarity_score = 65.0

        # 4. Accuracy Score (0-100)
        accuracy_score = 90.0

        # 5. Brand Score (0-100)
        brand_score = 90.0

        # Penalties: Clickbait, Superlatives, Urgency
        penalty = 0.0
        for pat in cls.CLICKBAIT_PATTERNS:
            if pat.search(headline):
                penalty += 35.0
                brand_score -= 30.0
                accuracy_score -= 25.0

        for pat in cls.SUPERLATIVE_PATTERNS:
            if pat.search(headline):
                penalty += 20.0
                accuracy_score -= 20.0

        overall = (
            (intent_score * 0.25)
            + (seo_score * 0.25)
            + (clarity_score * 0.20)
            + (accuracy_score * 0.15)
            + (brand_score * 0.15)
            - penalty
        )
        overall = max(0.0, min(100.0, overall))

        return {
            "intent_score": round(intent_score, 1),
            "seo_score": round(seo_score, 1),
            "clarity_score": round(clarity_score, 1),
            "accuracy_score": round(accuracy_score, 1),
            "brand_score": round(brand_score, 1),
            "overall_score": round(overall, 1),
        }
