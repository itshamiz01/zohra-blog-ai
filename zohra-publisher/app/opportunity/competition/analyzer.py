"""
Zohra — Competition & Content Gap Intelligence Engine.

Calculates Zohra Competition Score (0 to 100) based on observable SERP signals.
Never fabricates proprietary keyword difficulty metrics.
Discovers concrete structural content gaps (e.g., missing pricing, lack of workflow,
unaddressed limitations, regional availability gaps) and evaluates Information Gain potential.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.opportunity.serp.provider import SERPSnapshotData


@dataclass
class DetectedGap:
    gap_type: str
    description: str
    evidence: dict[str, Any]
    importance_score: float
    confidence_score: float


@dataclass
class CompetitionAnalysisResult:
    competition_score: float  # 0 to 100 (higher = harder)
    competition_opportunity_score: float  # 100 - competition_score
    saturation_score: float  # 0 to 100 (degree of SERP saturation)
    information_gain_score: float  # 0 to 100 (potential to add novel value)
    original_value_score: float  # 0 to 100
    serp_gap_score: float  # 0 to 100 (breadth of identified gaps)
    competitor_domains: list[str] = field(default_factory=list)
    competitor_urls: list[str] = field(default_factory=list)
    gaps: list[DetectedGap] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


class CompetitionAnalyzer:
    """Analyzes SERP competitors, content saturation, and structural gaps."""

    HIGH_AUTHORITY_DOMAINS = {
        "wikipedia.org", "techcrunch.com", "theverge.com", "forbes.com",
        "bloomberg.com", "reuters.com", "nytimes.com", "wsj.com",
        "cnet.com", "zdnet.com", "wired.com", "github.com", "microsoft.com",
        "apple.com", "google.com"
    }

    def analyze(self, snapshot: SERPSnapshotData) -> CompetitionAnalysisResult:
        results = snapshot.results
        query = snapshot.query.lower()
        if not results:
            # When no SERP results exist (emerging/zero-history query)
            return CompetitionAnalysisResult(
                competition_score=20.0,
                competition_opportunity_score=80.0,
                saturation_score=10.0,
                information_gain_score=85.0,
                original_value_score=85.0,
                serp_gap_score=75.0,
                reasons=["No existing dominant ranking pages detected (emerging topic)"],
            )

        # 1. Authority & Brand Dominance in Top 5
        top_5 = results[:5]
        official_in_top_3 = any(r.is_official_domain for r in results[:3])
        high_auth_count = sum(1 for r in top_5 if r.domain in self.HIGH_AUTHORITY_DOMAINS)
        forum_count = sum(1 for r in results if r.is_forum)

        # 2. Formula for Zohra Competition Score:
        # Base starts at 40
        comp_score = 40.0

        if official_in_top_3:
            comp_score += 25.0  # Official page in top 3 is hard to unseat

        # Each major authoritative domain adds competition
        comp_score += min(25.0, high_auth_count * 6.0)

        # Forum presence indicates weak formal editorial coverage -> lowers barrier to entry
        if forum_count >= 2:
            comp_score -= 15.0

        # Exact query match saturation in top titles
        exact_matches = sum(1 for r in results if all(w in r.title.lower() for w in query.split()[:3]))
        saturation_score = min(100.0, exact_matches * 12.0)
        comp_score += (saturation_score * 0.15)

        comp_score = round(min(98.0, max(10.0, comp_score)), 1)
        comp_opp_score = round(100.0 - comp_score, 1)

        # 3. Content Gap Detection (Observable evidence across snippets & titles)
        snippets_combined = " ".join(r.snippet.lower() for r in results if r.snippet)
        titles_combined = " ".join(r.title.lower() for r in results)
        combined_text = f"{titles_combined} {snippets_combined}"

        gaps: list[DetectedGap] = []
        analyzed_urls = [r.url for r in results[:6]]

        # Gap 1: Missing Pricing / Cost Clarity
        if any(term in query for term in ("price", "cost", "pricing", "free", "plan")) or "tool" in query:
            has_price_details = bool(re.search(r"(\$\d+|\/mo|free\s+tier|pricing\s+starts|per\s+month)", combined_text))
            if not has_price_details:
                gaps.append(
                    DetectedGap(
                        gap_type="missing_pricing",
                        description="Top ranking pages fail to provide explicit pricing tiers, monthly costs, or free plan limits.",
                        evidence={"analyzed_urls": analyzed_urls, "missing_dimension": "pricing_details"},
                        importance_score=85.0,
                        confidence_score=90.0,
                    )
                )

        # Gap 2: Lack of Practical Workflow / Step-by-Step Implementation
        if any(term in query for term in ("how to", "tutorial", "guide", "workflow", "setup")):
            has_steps = any(term in combined_text for term in ("step 1", "first,", "workflow", "setup guide", "install"))
            if not has_steps:
                gaps.append(
                    DetectedGap(
                        gap_type="lack_of_workflow",
                        description="Competitors describe theoretical features without concrete step-by-step implementation workflow.",
                        evidence={"analyzed_urls": analyzed_urls, "missing_dimension": "actionable_workflow"},
                        importance_score=90.0,
                        confidence_score=88.0,
                    )
                )

        # Gap 3: Missing Limitations / Trade-offs
        has_limitations = any(term in combined_text for term in ("limitation", "drawback", "cons", "trade-off", "not suitable for", "downsides"))
        if not has_limitations:
            gaps.append(
                DetectedGap(
                    gap_type="no_limitations",
                    description="Competitor articles provide generic promotional summaries without discussing real-world limitations or downsides.",
                    evidence={"analyzed_urls": analyzed_urls, "missing_dimension": "unbiased_limitations"},
                    importance_score=75.0,
                    confidence_score=85.0,
                )
            )

        # Gap 4: Regional Nuance / Availability (e.g. India, Europe, currency)
        if any(term in query for term in ("india", "uk", "europe", "availability", "global")) or "pricing" in query:
            has_regional = any(term in combined_text for term in ("india", "inr", "upi", "eu", "global availability", "supported countries"))
            if not has_regional:
                gaps.append(
                    DetectedGap(
                        gap_type="regional_gap",
                        description="No competitor provides regional pricing, availability nuances, or local payment methods.",
                        evidence={"analyzed_urls": analyzed_urls, "missing_dimension": "regional_coverage"},
                        importance_score=80.0,
                        confidence_score=92.0,
                    )
                )

        # Gap 5: Weak Comparison Tables / Structured Decision Framework
        if "vs" in query or "alternative" in query or "best" in query:
            has_matrix = "comparison table" in combined_text or "head to head" in combined_text
            if not has_matrix:
                gaps.append(
                    DetectedGap(
                        gap_type="weak_comparisons",
                        description="Lacks structured side-by-side comparison matrix; competitors rely on vague narrative text.",
                        evidence={"analyzed_urls": analyzed_urls, "missing_dimension": "structured_comparison_matrix"},
                        importance_score=85.0,
                        confidence_score=88.0,
                    )
                )

        # 4. Synthesize Scores
        serp_gap_score = min(100.0, max(25.0, len(gaps) * 22.0 + 20.0))
        information_gain_score = min(100.0, max(20.0, (serp_gap_score * 0.60) + (comp_opp_score * 0.40)))
        original_value_score = round((information_gain_score * 0.70) + (serp_gap_score * 0.30), 1)

        # Build diagnostic reasoning
        reasons: list[str] = []
        if comp_score > 75:
            reasons.append("High competition: authoritative media or official portal dominates top positions")
        elif comp_score < 45:
            reasons.append("Favorable competition: ranking pages are forums or generalist articles without deep coverage")

        if gaps:
            reasons.append(f"Identified {len(gaps)} structural content gaps: {', '.join(g.gap_type for g in gaps)}")

        return CompetitionAnalysisResult(
            competition_score=comp_score,
            competition_opportunity_score=comp_opp_score,
            saturation_score=round(saturation_score, 1),
            information_gain_score=round(information_gain_score, 1),
            original_value_score=original_value_score,
            serp_gap_score=round(serp_gap_score, 1),
            competitor_domains=[r.domain for r in results[:6]],
            competitor_urls=[r.url for r in results if not r.is_official_domain][:5],
            gaps=gaps,
            reasons=reasons,
        )
