"""
Zohra — Part 9 Hypothesis Engine.

Implements Sections 14, 15, 16 of Part 9 Master Prompt:
- Formulates evidence-grounded hypotheses from observed performance data
- Maintains strict separation between observed facts and causal hypotheses
- Defines explicit mechanisms, primary target metrics, and guardrail metrics
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.db.models.optimization import RiskClass


@dataclass
class StructuredHypothesis:
    """Rigorous scientific hypothesis for an optimization proposal."""

    observation: str
    hypothesis: str
    proposed_change: str
    expected_mechanism: str
    primary_metric: str
    guardrail_metrics: list[str]
    confidence: float
    risk: str
    possible_causes: list[str] = field(default_factory=list)
    confounding_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OptimizationHypothesisEngine:
    """Generates structured hypotheses explaining why changes might improve performance."""

    @classmethod
    def generate_hypothesis(
        cls,
        candidate_type: str,
        observed_problem: str,
        evidence: dict[str, Any],
        affected_queries: list[str] | None = None,
        article_title: str | None = None,
    ) -> StructuredHypothesis:
        """
        Builds a verified StructuredHypothesis from observation data.
        """
        c_type = candidate_type.upper().replace("-", "_")
        queries = affected_queries or []
        top_query = queries[0] if queries else "the dominant search queries"

        # Case 1: Low CTR Optimization
        if "CTR" in c_type or c_type == "CTR_IMPROVEMENT":
            impressions = evidence.get("impressions", evidence.get("current_impressions", 0))
            avg_pos = evidence.get("avg_position", evidence.get("current_position", 0.0))
            observed = (
                f"Article receives {impressions:,} impressions with an average Search Console "
                f"position of {avg_pos:.1f}, but CTR is materially below the site's benchmark."
                if impressions > 0 else observed_problem
            )
            return StructuredHypothesis(
                observation=observed,
                hypothesis="The search snippet (title and meta description) may not align strongly enough with the primary user intent for dominant high-impression queries.",
                proposed_change=f"Refine the title and meta description to communicate the primary benefit for '{top_query}' while preserving factual accuracy.",
                expected_mechanism="Better semantic alignment between user search intent and the visible SERP snippet may increase organic click-through rate without sacrificing rankings.",
                primary_metric="search_console_ctr",
                guardrail_metrics=["impressions", "avg_position", "clicks"],
                confidence=min(0.85, max(0.60, float(evidence.get("confidence", 0.75)))),
                risk=RiskClass.CLASS_A.value,
                possible_causes=[
                    "Snippet wording is generic or vague",
                    "Title does not directly address the searcher's specific question",
                    "Competing SERP results provide clearer value propositions",
                ],
                confounding_factors=[
                    "SERP feature layout shifts (featured snippets, video packs)",
                    "Brand-name presence in competing titles",
                ],
            )

        # Case 2: Page Two Striking Distance
        if "PAGE_TWO" in c_type or c_type == "PAGE_2":
            return StructuredHypothesis(
                observation=observed_problem or f"Article ranks in striking distance (positions 11-20) for query '{top_query}'.",
                hypothesis=f"The page has established baseline topical relevance for '{top_query}', but lacks sufficient topical depth and contextual internal links to cross into Page 1.",
                proposed_change="Expand coverage of subtopics directly answering the query intent and add contextual internal links from higher-authority related pages.",
                expected_mechanism="Strengthening topical completeness and internal PageRank flow signals to search engines that the article is a comprehensive primary resource.",
                primary_metric="avg_position",
                guardrail_metrics=["impressions", "clicks", "bounce_rate"],
                confidence=0.78,
                risk=RiskClass.CLASS_B.value,
                possible_causes=[
                    "Missing secondary questions answered by top 5 competitors",
                    "Insufficient internal links from relevant cluster pages",
                ],
                confounding_factors=[
                    "High domain authority of top 3 competing sites",
                    "Intent shifts toward commercial products rather than informational guides",
                ],
            )

        # Case 3: Cannibalization
        if "CANNIBALIZATION" in c_type:
            competing = evidence.get("competing_urls", [])
            return StructuredHypothesis(
                observation=observed_problem or f"Multiple pages split impressions for query '{top_query}'.",
                hypothesis="Search engines are unable to identify a single authoritative canonical source for this query cluster across multiple competing internal pages.",
                proposed_change="Differentiate intent clearly between pages, or consolidate query coverage into the primary canonical article.",
                expected_mechanism="Removing internal topical ambiguity consolidates ranking signals onto a single targeted URL.",
                primary_metric="clicks",
                guardrail_metrics=["impressions", "site_total_clicks"],
                confidence=0.82,
                risk=RiskClass.CLASS_C.value if len(competing) > 1 else RiskClass.CLASS_B.value,
                possible_causes=[
                    "Keyword overlap across separate articles without distinct subtopic scopes",
                    "Similar headline and heading structures across related posts",
                ],
                confounding_factors=[
                    "External backlinks pointing to both competing internal pages",
                ],
            )

        # Case 4: Content Decay & Refresh
        if "REFRESH" in c_type or "DECLINE" in c_type or "DECAY" in c_type:
            return StructuredHypothesis(
                observation=observed_problem or "Organic impressions and clicks have experienced sustained decline over consecutive 28-day windows.",
                hypothesis="Content contains outdated references, stale statistics, or lacks coverage of recent developments expected by searchers.",
                proposed_change="Perform a verified content refresh updating time-sensitive claims, refreshing statistics, and aligning headings with current query volume.",
                expected_mechanism="Fresh, accurate, and comprehensively updated coverage signals freshness and restores search relevance.",
                primary_metric="clicks",
                guardrail_metrics=["avg_position", "impressions"],
                confidence=0.80,
                risk=RiskClass.CLASS_B.value,
                possible_causes=[
                    "Competitors published newer, more up-to-date guides",
                    "Year-specific information is now perceived as obsolete by users",
                ],
                confounding_factors=[
                    "General industry search volume seasonality",
                    "Algorithm updates rewarding newer media formats",
                ],
            )

        # Case 5: Query Expansion
        if "QUERY_EXPANSION" in c_type or "UNEXPECTED_QUERY" in c_type:
            return StructuredHypothesis(
                observation=observed_problem or f"Article attracts rising impressions for query '{top_query}' which is not explicitly covered in dedicated headings.",
                hypothesis=f"Search engines consider the article relevant for '{top_query}', but users may not find a direct, prominent answer in the text.",
                proposed_change=f"Add a dedicated focused section answering '{top_query}' with verified facts.",
                expected_mechanism="Explicitly satisfying this emerging search query improves dwell time and captures higher ranking positions for long-tail queries.",
                primary_metric="clicks",
                guardrail_metrics=["avg_position", "primary_query_rankings"],
                confidence=0.76,
                risk=RiskClass.CLASS_B.value,
                possible_causes=[
                    "Query represents a natural corollary question to the article's core theme",
                ],
                confounding_factors=[
                    "Query might represent a distinct intent requiring a standalone article",
                ],
            )

        # Default Generic Hypothesis
        return StructuredHypothesis(
            observation=observed_problem or "Article exhibits performance optimization opportunities.",
            hypothesis=f"Optimization of {c_type} will address observed ranking constraints.",
            proposed_change=f"Execute controlled test for {c_type}.",
            expected_mechanism="Improves relevance and user engagement.",
            primary_metric="clicks",
            guardrail_metrics=["impressions", "avg_position"],
            confidence=0.70,
            risk=RiskClass.CLASS_A.value,
            possible_causes=["Suboptimal metadata or structure"],
            confounding_factors=["Market trend changes"],
        )
