"""
Zohra — Source Suitability Engine.

Maps claim and question categories to preferred evidence types (e.g. pricing -> official site,
software capabilities -> release notes, user sentiment -> community discussions).
"""

from __future__ import annotations

from app.schemas.research import SourceType


class SourceSuitabilityEngine:
    """Evaluates how suitable a given source type is for verifying a specific claim or question type."""

    # Matrix: claim_type/question_type -> preferred source_types with weight (0.0 to 1.0)
    SUITABILITY_MATRIX: dict[str, dict[str, float]] = {
        "pricing": {
            SourceType.OFFICIAL_DOCUMENTATION.value: 1.0,
            SourceType.OFFICIAL_ANNOUNCEMENT.value: 0.95,
            SourceType.REGULATORY_FILING.value: 0.9,
            SourceType.NEWS_REPORT.value: 0.65,
            SourceType.REVIEW.value: 0.6,
            SourceType.INDUSTRY_BLOG.value: 0.5,
            SourceType.COMMUNITY_FORUM.value: 0.25,
        },
        "capability": {
            SourceType.OFFICIAL_DOCUMENTATION.value: 1.0,
            SourceType.OFFICIAL_ANNOUNCEMENT.value: 0.9,
            SourceType.ACADEMIC_PAPER.value: 0.85,
            SourceType.REVIEW.value: 0.75,
            SourceType.NEWS_REPORT.value: 0.7,
            SourceType.INDUSTRY_BLOG.value: 0.6,
            SourceType.COMMUNITY_FORUM.value: 0.4,
        },
        "technical": {
            SourceType.OFFICIAL_DOCUMENTATION.value: 1.0,
            SourceType.ACADEMIC_PAPER.value: 0.95,
            SourceType.OFFICIAL_ANNOUNCEMENT.value: 0.85,
            SourceType.REVIEW.value: 0.7,
            SourceType.INDUSTRY_BLOG.value: 0.65,
            SourceType.COMMUNITY_FORUM.value: 0.5,
        },
        "limitation": {
            SourceType.OFFICIAL_DOCUMENTATION.value: 0.8,
            SourceType.REVIEW.value: 0.95,
            SourceType.COMMUNITY_FORUM.value: 0.9,
            SourceType.INDUSTRY_BLOG.value: 0.8,
            SourceType.NEWS_REPORT.value: 0.7,
        },
        "user_experience": {
            SourceType.COMMUNITY_FORUM.value: 1.0,
            SourceType.REVIEW.value: 0.9,
            SourceType.INDUSTRY_BLOG.value: 0.7,
            SourceType.NEWS_REPORT.value: 0.6,
            SourceType.OFFICIAL_DOCUMENTATION.value: 0.3,
        },
        "timeline": {
            SourceType.OFFICIAL_ANNOUNCEMENT.value: 1.0,
            SourceType.OFFICIAL_DOCUMENTATION.value: 0.95,
            SourceType.NEWS_REPORT.value: 0.85,
            SourceType.REGULATORY_FILING.value: 0.85,
            SourceType.INDUSTRY_BLOG.value: 0.5,
            SourceType.COMMUNITY_FORUM.value: 0.3,
        },
        "legal": {
            SourceType.REGULATORY_FILING.value: 1.0,
            SourceType.OFFICIAL_DOCUMENTATION.value: 0.95,
            SourceType.OFFICIAL_ANNOUNCEMENT.value: 0.85,
            SourceType.NEWS_REPORT.value: 0.75,
            SourceType.COMMUNITY_FORUM.value: 0.2,
        },
    }

    @classmethod
    def get_suitability_score(
        cls,
        target_category: str,
        source_type: str,
        is_primary_source: bool = False,
    ) -> float:
        cat_lower = target_category.lower()
        # Find matching category in matrix
        matched_cat = None
        for key in cls.SUITABILITY_MATRIX:
            if key in cat_lower or cat_lower in key:
                matched_cat = key
                break

        if not matched_cat:
            # Default fallback suitability
            base = 0.75 if is_primary_source else 0.60
            return base

        suitability_map = cls.SUITABILITY_MATRIX[matched_cat]
        score = suitability_map.get(source_type, 0.5)

        # Primary source boost
        if is_primary_source:
            score = min(1.0, score + 0.15)

        return round(score, 2)
