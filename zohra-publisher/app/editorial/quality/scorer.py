"""
Zohra — Draft Quality Scorer (Part 5).

Implements the canonical 100-point editorial quality formula from Section 116:
Intent Satisfaction (20), Grounding (20), Information Gain (15), Clarity (10),
Structure (10), SEO Quality (10), Citation Quality (5), Readability (5), Brand Voice (5).
Applies penalties and enforces quality gates for Part 6 eligibility.
"""

from __future__ import annotations

from app.editorial.seo.anti_slop import AISlopDetector
from app.schemas.editorial import DraftQualityScores
from app.schemas.research import FinalResearchPackage


class DraftQualityScorer:
    """Evaluates multi-dimensional draft quality and quality gate eligibility."""

    @classmethod
    def score_draft(
        cls,
        content: str,
        title: str,
        primary_keyword: str,
        grounding_score: float,
        seo_content_score: float,
        research_pkg: FinalResearchPackage,
        is_high_risk: bool = False,
        brand_voice_applied: bool = True,
    ) -> DraftQualityScores:
        # 1. Slop & Redundancy Analysis
        slop_data = AISlopDetector.evaluate(content)
        slop_penalty = slop_data["slop_penalty"]
        redundancy_score = slop_data["redundancy_score"]

        # 2. Intent Satisfaction (0-20)
        # Check if primary keyword and topic questions are addressed
        pk_in_content = primary_keyword.lower() in content.lower()
        answered_ratio = len(research_pkg.research_questions.answered) / max(1, (len(research_pkg.research_questions.answered) + len(research_pkg.research_questions.unanswered)))
        intent_sat = 15.0 if pk_in_content else 10.0
        intent_sat += (answered_ratio * 5.0)

        # 3. Grounding Component (0-20)
        # Direct mapping from 0-100 grounding score
        grounding_comp = (grounding_score / 100.0) * 20.0

        # 4. Information Gain (0-15)
        # Based on primary sources present, verified numbers, and unique content gaps filled
        has_primary = bool(research_pkg.primary_sources)
        has_nums = bool(research_pkg.important_numbers)
        has_limits = bool(research_pkg.limitations)
        info_gain = 7.0
        if has_primary:
            info_gain += 3.0
        if has_nums:
            info_gain += 3.0
        if has_limits:
            info_gain += 2.0
        info_gain = min(15.0, info_gain)

        # 5. Clarity (0-10)
        # Penalize for low density or very high redundancy
        clarity = 10.0 - (slop_penalty * 0.1) - ((100.0 - redundancy_score) * 0.05)
        clarity = max(2.0, min(10.0, clarity))

        # 6. Structure (0-10)
        # Heading progression and markdown format
        has_h1 = content.count("\n# ") > 0 or content.startswith("# ")
        h2_count = content.count("\n## ")
        structure = 5.0
        if has_h1:
            structure += 2.0
        if h2_count >= 3:
            structure += 3.0
        structure = min(10.0, structure)

        # 7. SEO Quality (0-10)
        seo_comp = (seo_content_score / 100.0) * 10.0

        # 8. Citation Quality (0-5)
        # Ratio of safe claims with citation mapping
        cited_ratio = len(research_pkg.citation_map) / max(1, len(research_pkg.verified_facts))
        citation_comp = min(5.0, cited_ratio * 5.0)

        # 9. Readability (0-5)
        readability_comp = (redundancy_score / 100.0) * 5.0

        # 10. Brand Voice (0-5)
        brand_comp = 5.0 if brand_voice_applied else 4.0

        # Total Raw Score
        total_raw = (
            intent_sat
            + grounding_comp
            + info_gain
            + clarity
            + structure
            + seo_comp
            + citation_comp
            + readability_comp
            + brand_comp
            - (slop_penalty * 0.15)
        )
        total_quality = round(max(0.0, min(100.0, total_raw)), 1)

        # Classification
        if total_quality >= 95.0:
            classification = "EXCEPTIONAL_DRAFT"
        elif total_quality >= 85.0:
            classification = "STRONG_DRAFT"
        elif total_quality >= 75.0:
            classification = "PART_6_ELIGIBLE"
        elif total_quality >= 65.0:
            classification = "REVISION_REQUIRED"
        elif total_quality >= 50.0:
            classification = "MAJOR_REVISION"
        else:
            classification = "REJECT"

        # Quality Gate Check
        min_quality = 90.0 if is_high_risk else 80.0
        min_grounding = 95.0 if is_high_risk else 90.0
        gate_passed = (total_quality >= min_quality) and (grounding_score >= min_grounding)

        return DraftQualityScores(
            intent_satisfaction=round(intent_sat * 5.0, 1),  # Normalized to 0-100 for display
            grounding=round(grounding_score, 1),
            information_gain=round(info_gain * (100.0 / 15.0), 1),
            clarity=round(clarity * 10.0, 1),
            structure=round(structure * 10.0, 1),
            seo_content=round(seo_content_score, 1),
            citation_quality=round(citation_comp * 20.0, 1),
            readability=round(readability_comp * 20.0, 1),
            brand_voice=round(brand_comp * 20.0, 1),
            draft_quality=total_quality,
            quality_gate_passed=gate_passed,
            classification=classification,
        )
