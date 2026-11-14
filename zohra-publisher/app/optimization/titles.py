"""
Zohra — Part 9 Title & Meta Optimization Engine.

Implements Sections 32 to 37 of Part 9 Master Prompt:
- Multi-candidate title generation and scoring (intent alignment, clarity, accuracy, click appeal)
- Anti-clickbait & anti-sensationalism safety filters (rejects "Guaranteed", "Secret Trick", etc.)
- Strict factual consistency validation against underlying article content
- Query-intent aligned meta description generation
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PROHIBITED_CLICKBAIT_PHRASES = [
    r"\bguaranteed\b",
    r"\bsecret google trick\b",
    r"\b100% success\b",
    r"\binstant results\b",
    r"\byou won't believe\b",
    r"\bshocking truth\b",
    r"\bone weird trick\b",
    r"\bblow your mind\b",
    r"\bguarantee\b",
]


@dataclass
class TitleCandidate:
    title: str
    intent_alignment_score: float   # 0.0 - 1.0
    clarity_score: float            # 0.0 - 1.0
    accuracy_score: float           # 0.0 - 1.0
    keyword_relevance_score: float  # 0.0 - 1.0
    click_appeal_score: float       # 0.0 - 1.0
    brand_fit_score: float          # 0.0 - 1.0
    spam_risk_score: float          # 0.0 - 1.0 (lower is better)
    composite_score: float          # 0.0 - 1.0
    is_safe: bool = True
    rejection_reason: str | None = None


@dataclass
class MetaDescriptionCandidate:
    meta_description: str
    character_count: int
    intent_fit_score: float
    includes_target_keyword: bool
    is_safe: bool = True


class TitleOptimizationEngine:
    """Generates and evaluates search-optimized, factually grounded title proposals."""

    @classmethod
    def check_sensationalism_and_clickbait(cls, title: str) -> tuple[bool, str | None]:
        """
        Validates that a title contains no deceptive, sensationalist, or spam clickbait.
        """
        t_lower = title.lower()
        for pattern in PROHIBITED_CLICKBAIT_PHRASES:
            if re.search(pattern, t_lower):
                return False, f"Title contains prohibited clickbait phrase matching pattern: {pattern}"

        # Excessive punctuation check (e.g. !!!, ???, all caps)
        if "!!!" in title or "???" in title:
            return False, "Title contains sensationalist excessive punctuation"
        words = re.findall(r"\b[A-Z]{3,}\b", title)
        # Avoid ALL CAPS screams
        if len(words) >= 3 and not any(w in {"SEO", "API", "GSC", "URL", "HTML", "JSON", "AI", "LLM"} for w in words):
            return False, "Title contains excessive all-caps words"

        return True, None

    @classmethod
    def check_factual_consistency(cls, candidate_title: str, article_body: str) -> tuple[bool, str | None]:
        """
        Ensures claims in the proposed title (e.g. numbers, specific entities) are verified in article body.
        """
        # 1. Number extraction check (e.g. "10 Tools" requires at least 10 items or sections)
        number_match = re.search(r"\b(\d{1,2})\b", candidate_title)
        if number_match:
            num = int(number_match.group(1))
            # If the title claims a specific count like "7 Steps" or "10 Tools"
            if num >= 4:
                # Check if the number or sufficient headings exist in the body
                headings = re.findall(r"^#{2,3}\s+(.+)$", article_body, flags=re.MULTILINE)
                num_in_body = str(num) in article_body
                if not num_in_body and len(headings) < num:
                    return False, f"Title claims {num} items, but article body only has {len(headings)} sections and does not mention {num}"

        # 2. Testing/Case-study claim verification
        title_lower = candidate_title.lower()
        if "we tested" in title_lower or "our hands-on review" in title_lower:
            if "we tested" not in article_body.lower() and "hands-on" not in article_body.lower():
                return False, "Title claims first-party hands-on testing not documented in the article body"

        return True, None

    @classmethod
    def generate_and_rank_candidates(
        cls,
        current_title: str,
        target_keyword: str,
        dominant_queries: list[str],
        article_body: str,
        brand_name: str | None = None,
    ) -> list[TitleCandidate]:
        """
        Generates structured alternative titles and ranks them with explicit safety scores.
        """
        top_query = dominant_queries[0] if dominant_queries else target_keyword
        norm_query = top_query.title()

        # Build candidate variants
        raw_candidates = [
            current_title,
            f"{norm_query}: Complete Step-by-Step Guide",
            f"How to {norm_query} (Best Practices & Examples)",
            f"{norm_query} Explained: What You Need to Know",
            f"The Practical Guide to {norm_query}",
        ]

        scored: list[TitleCandidate] = []
        for cand in raw_candidates:
            is_clickbait_safe, cb_err = cls.check_sensationalism_and_clickbait(cand)
            is_factual_safe, fc_err = cls.check_factual_consistency(cand, article_body)

            is_safe = is_clickbait_safe and is_factual_safe
            rejection = cb_err or fc_err

            # Scoring heuristics
            kw_match = 1.0 if target_keyword.lower() in cand.lower() else 0.7
            query_match = 1.0 if top_query.lower() in cand.lower() else 0.6
            intent_score = round((kw_match + query_match) / 2.0, 2)
            clarity = 0.9 if 40 <= len(cand) <= 65 else 0.7
            accuracy = 1.0 if is_factual_safe else 0.2
            appeal = 0.85 if is_clickbait_safe else 0.1
            brand_fit = 0.9

            spam_risk = 0.05 if is_safe else 0.95
            composite = round(
                (intent_score * 0.3)
                + (clarity * 0.2)
                + (accuracy * 0.25)
                + (appeal * 0.15)
                + (brand_fit * 0.1)
                - (spam_risk * 0.4),
                2,
            )

            scored.append(
                TitleCandidate(
                    title=cand,
                    intent_alignment_score=intent_score,
                    clarity_score=clarity,
                    accuracy_score=accuracy,
                    keyword_relevance_score=kw_match,
                    click_appeal_score=appeal,
                    brand_fit_score=brand_fit,
                    spam_risk_score=spam_risk,
                    composite_score=max(0.0, composite),
                    is_safe=is_safe,
                    rejection_reason=rejection,
                )
            )

        # Sort descending by composite score, safe candidates first
        scored.sort(key=lambda c: (c.is_safe, c.composite_score), reverse=True)
        return scored


class MetaOptimizationEngine:
    """Produces search-intent aligned meta descriptions within character constraints."""

    @classmethod
    def generate_meta_description(
        cls,
        target_keyword: str,
        dominant_queries: list[str],
        article_summary: str,
        max_chars: int = 158,
    ) -> MetaDescriptionCandidate:
        """
        Produces a concise meta description summarizing the primary benefit.
        """
        top_query = dominant_queries[0] if dominant_queries else target_keyword
        base = (
            f"Learn everything about {top_query}. "
            f"Explore practical insights, clear explanations, and verified guidance."
        )

        if len(base) > max_chars:
            base = base[: max_chars - 3] + "..."

        includes_kw = target_keyword.lower() in base.lower()
        return MetaDescriptionCandidate(
            meta_description=base,
            character_count=len(base),
            intent_fit_score=0.88,
            includes_target_keyword=includes_kw,
            is_safe=True,
        )
