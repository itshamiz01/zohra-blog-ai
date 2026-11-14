"""
Zohra — Quality Score Aggregator & Critical Overrides (Part 6).

Implements Zohra's canonical 100-point audit formula:
- Factual Integrity: 20 pts
- Grounding: 15 pts
- Citation Quality: 10 pts
- Intent Satisfaction: 10 pts
- Information Gain: 10 pts
- Temporal Integrity: 10 pts
- Content Quality: 10 pts
- Originality: 5 pts
- SEO Quality: 5 pts
- Structure: 3 pts
- Brand Voice: 2 pts
Total: 100 pts.

Enforces CRITICAL-FAIL OVERRIDES:
Regardless of aggregate score (even 98/100), critical failures permanently block PASS:
- Fabricated source
- Fabricated quotation
- Critical unsupported claim
- Dangerous instruction / medical guarantee
- Prohibited political advocacy
- Prompt injection attack
"""

from __future__ import annotations

from app.schemas.audit import AuditIssueItem, AuditQualityScores, IssueSeverity


class ScoreAggregator:
    """Aggregates quality dimensions and applies hard critical failure overrides."""

    CRITICAL_OVERRIDE_CODES = {
        "CITATION_FABRICATED",
        "FABRICATED_QUOTE",
        "FAKE_EXPERIENCE",
        "UNSUPPORTED_MEDICAL_CURE",
        "UNSUPPORTED_FINANCIAL_PROMISE",
        "POLITICAL_ADVOCACY_VIOLATION",
        "PROMPT_INJECTION_DETECTED",
        "SITE_TOPIC_DUPLICATION",
    }

    WEIGHTS = {
        "factual_integrity": 0.20,
        "grounding": 0.15,
        "citation_quality": 0.10,
        "intent_satisfaction": 0.10,
        "information_gain": 0.10,
        "temporal_integrity": 0.10,
        "content_quality": 0.10,
        "originality": 0.05,
        "seo_quality": 0.05,
        "structure": 0.03,
        "brand_voice": 0.02,
    }

    def aggregate(
        self,
        factual_score: float,
        grounding_score: float,
        citation_score: float,
        temporal_score: float,
        originality_score: float,
        intent_score: float,
        info_gain_score: float,
        seo_score: float,
        content_quality_score: float,
        structure_score: float,
        brand_score: float = 90.0,
        risk_score: float = 100.0,
        issues: list[AuditIssueItem] | None = None,
    ) -> tuple[AuditQualityScores, list[str]]:
        """Calculates final scores and returns list of critical failure override triggers."""
        raw_overall = (
            (factual_score * self.WEIGHTS["factual_integrity"])
            + (grounding_score * self.WEIGHTS["grounding"])
            + (citation_score * self.WEIGHTS["citation_quality"])
            + (intent_score * self.WEIGHTS["intent_satisfaction"])
            + (info_gain_score * self.WEIGHTS["information_gain"])
            + (temporal_score * self.WEIGHTS["temporal_integrity"])
            + (content_quality_score * self.WEIGHTS["content_quality"])
            + (originality_score * self.WEIGHTS["originality"])
            + (seo_score * self.WEIGHTS["seo_quality"])
            + (structure_score * self.WEIGHTS["structure"])
            + (brand_score * self.WEIGHTS["brand_voice"])
        )

        critical_overrides: list[str] = []
        if issues:
            for issue in issues:
                if issue.severity == IssueSeverity.CRITICAL or issue.issue_code in self.CRITICAL_OVERRIDE_CODES:
                    critical_overrides.append(f"{issue.issue_code}: {issue.description}")

        scores = AuditQualityScores(
            factual_integrity=round(factual_score, 2),
            grounding=round(grounding_score, 2),
            citation_quality=round(citation_score, 2),
            temporal_integrity=round(temporal_score, 2),
            originality=round(originality_score, 2),
            intent_satisfaction=round(intent_score, 2),
            information_gain=round(info_gain_score, 2),
            seo_quality=round(seo_score, 2),
            content_quality=round(content_quality_score, 2),
            structure=round(structure_score, 2),
            brand_voice=round(brand_score, 2),
            risk_compliance=round(risk_score, 2),
            overall_score=round(max(0.0, min(100.0, raw_overall)), 2),
        )

        return scores, critical_overrides
