"""
Zohra — Part 9 Content Consolidation Analyzer.

Implements Sections 44, 45, 46, 47 of Part 9 Master Prompt:
- Analyzes search cannibalization and semantic overlap across multiple pages
- Evaluates options: KEEP_SEPARATE, DIFFERENTIATE, MERGE, REDIRECT, CANONICAL_REVIEW, NO_ACTION
- Enforces strict safety gates: mergers and redirects are Class C (High Risk) requiring human approval
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from app.db.models.optimization import RiskClass


class ConsolidationAction(str, Enum):
    KEEP_SEPARATE = "KEEP_SEPARATE"
    DIFFERENTIATE = "DIFFERENTIATE"
    MERGE = "MERGE"
    REDIRECT = "REDIRECT"
    CANONICAL_REVIEW = "CANONICAL_REVIEW"
    NO_ACTION = "NO_ACTION"


@dataclass
class PageCannibalizationData:
    article_id: str
    url: str
    title: str
    clicks: int
    impressions: int
    avg_position: float
    age_days: int = 30
    inbound_internal_links: int = 5


@dataclass
class ConsolidationPlan:
    query: str
    recommended_action: ConsolidationAction
    risk_class: RiskClass
    human_approval_required: bool
    primary_article_id: str | None
    secondary_article_id: str | None
    explanation: str
    prerequisites: list[str] = field(default_factory=list)
    rollback_safeguards: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recommended_action"] = self.recommended_action.value
        d["risk_class"] = self.risk_class.value
        return d


class ContentConsolidationAnalyzer:
    """Evaluates cannibalization conflicts and formulates safe consolidation strategies."""

    @classmethod
    def analyze_cannibalization(
        cls,
        query: str,
        competing_pages: list[PageCannibalizationData],
        ownership_volatility: int = 0,
    ) -> ConsolidationPlan:
        """
        Analyzes 2 or more competing pages and selects the safest, most effective resolution.
        """
        if len(competing_pages) < 2:
            return ConsolidationPlan(
                query=query,
                recommended_action=ConsolidationAction.NO_ACTION,
                risk_class=RiskClass.CLASS_A,
                human_approval_required=False,
                primary_article_id=competing_pages[0].article_id if competing_pages else None,
                secondary_article_id=None,
                explanation="Fewer than 2 competing pages detected for this query cluster.",
            )

        # Sort pages by clicks (primary signal) then impressions
        sorted_pages = sorted(competing_pages, key=lambda p: (p.clicks, p.impressions), reverse=True)
        primary = sorted_pages[0]
        secondary = sorted_pages[1]

        total_clicks = sum(p.clicks for p in competing_pages)
        total_impr = sum(p.impressions for p in competing_pages)

        # If total volume is negligible, do not perform risky surgery
        if total_impr < 200:
            return ConsolidationPlan(
                query=query,
                recommended_action=ConsolidationAction.NO_ACTION,
                risk_class=RiskClass.CLASS_A,
                human_approval_required=False,
                primary_article_id=primary.article_id,
                secondary_article_id=secondary.article_id,
                explanation="Cannibalization impression volume is below the statistical action threshold (< 200 impressions).",
            )

        # Case 1: Primary page dominates (e.g. > 85% of clicks) and secondary has very few clicks
        # Recommendation: DIFFERENTIATE (sharpen headings) or CANONICAL_REVIEW
        primary_share = (primary.clicks / max(1, total_clicks))
        if primary_share > 0.85 and secondary.clicks <= 5:
            return ConsolidationPlan(
                query=query,
                recommended_action=ConsolidationAction.DIFFERENTIATE,
                risk_class=RiskClass.CLASS_B,
                human_approval_required=False,
                primary_article_id=primary.article_id,
                secondary_article_id=secondary.article_id,
                explanation=(
                    f"Page '{primary.url}' captures {primary_share:.0%} of clicks. "
                    f"Recommend differentiating secondary page '{secondary.url}' by adjusting subheadings away from '{query}'."
                ),
                prerequisites=["Verify secondary page targets a distinct sub-intent"],
            )

        # Case 2: Severe volatile split (e.g. 50/50 split with ranking volatility)
        # Recommendation: MERGE or REDIRECT
        if secondary.clicks > 15 and secondary.impressions > 500:
            # Substantial traffic on both pages -> High-risk merger requiring human sign-off
            return ConsolidationPlan(
                query=query,
                recommended_action=ConsolidationAction.MERGE,
                risk_class=RiskClass.CLASS_C,
                human_approval_required=True,
                primary_article_id=primary.article_id,
                secondary_article_id=secondary.article_id,
                explanation=(
                    f"Severe cannibalization on '{query}' across '{primary.url}' ({primary.clicks} clicks) "
                    f"and '{secondary.url}' ({secondary.clicks} clicks). Proposing to absorb unique sections of secondary into primary."
                ),
                prerequisites=[
                    "Human editorial approval required",
                    "Audit inbound backlinks and internal links to secondary page",
                    "Verify Part 6 approval of combined draft before publishing",
                ],
                rollback_safeguards=["Preserve full content snapshot of secondary article before merger"],
            )

        # Default: Propose 301 redirect if secondary is thin
        return ConsolidationPlan(
            query=query,
            recommended_action=ConsolidationAction.REDIRECT,
            risk_class=RiskClass.CLASS_C,
            human_approval_required=True,
            primary_article_id=primary.article_id,
            secondary_article_id=secondary.article_id,
            explanation=(
                f"Secondary page '{secondary.url}' has lower overall engagement. "
                f"Propose 301 permanent redirect to primary authority '{primary.url}'."
            ),
            prerequisites=["Human approval required for URL redirection"],
            rollback_safeguards=["Redirect table rollback entry must be generated"],
        )
