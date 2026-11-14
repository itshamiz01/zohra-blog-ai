"""
Zohra — Part 9 Portfolio Allocation & Content Investment Decision Engine.

Implements Sections 195 to 205, 273 to 275 of Part 9 Master Prompt:
- Balances content portfolio across buckets: CORE_EVERGREEN, TRENDING, NEWS, COMMERCIAL, REFRESH, EXPERIMENTAL
- Controls exploration budget (e.g. 85% proven / 15% exploration) and throttles when limit exceeded
- Content Investment Decision Engine comparing: REFRESH_SCORE vs NEW_ARTICLE_SCORE vs NO_ACTION_SCORE
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ContentBucket(str, Enum):
    CORE_EVERGREEN = "CORE_EVERGREEN"
    TRENDING = "TRENDING"
    NEWS = "NEWS"
    COMMERCIAL = "COMMERCIAL"
    REFRESH = "REFRESH"
    EXPERIMENTAL = "EXPERIMENTAL"


class InvestmentChoice(str, Enum):
    REFRESH_EXISTING = "REFRESH_EXISTING"
    CREATE_NEW_ARTICLE = "CREATE_NEW_ARTICLE"
    DO_NOTHING = "DO_NOTHING"


@dataclass
class PortfolioAllocationResult:
    target_allocations: dict[str, float]
    current_allocations: dict[str, float]
    exploration_ratio: float
    exploration_budget_exceeded: bool
    can_publish_experimental: bool
    recommendation: str


@dataclass
class InvestmentDecisionResult:
    choice: InvestmentChoice
    refresh_score: float
    new_article_score: float
    no_action_score: float
    target_article_id: str | None
    cannibalization_risk: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["choice"] = self.choice.value
        return d


class StrategyAllocationEngine:
    """Manages site content portfolio targets and exploration budget bounds."""

    DEFAULT_ALLOCATION = {
        ContentBucket.CORE_EVERGREEN.value: 0.40,
        ContentBucket.TRENDING.value: 0.20,
        ContentBucket.REFRESH.value: 0.15,
        ContentBucket.NEWS.value: 0.10,
        ContentBucket.COMMERCIAL.value: 0.05,
        ContentBucket.EXPERIMENTAL.value: 0.10,
    }

    @classmethod
    def evaluate_portfolio_budget(
        cls,
        current_counts: dict[str, int],
        configured_allocations: dict[str, float] | None = None,
        max_exploration_ratio: float = 0.15,
    ) -> PortfolioAllocationResult:
        """
        Calculates whether current publication distribution is within targets and
        checks exploration bounds (Sections 196, 273, Test AR).
        """
        targets = configured_allocations or cls.DEFAULT_ALLOCATION
        total_articles = max(1, sum(current_counts.values()))

        current_ratios: dict[str, float] = {}
        for b_name in targets.keys():
            count = current_counts.get(b_name, 0)
            current_ratios[b_name] = round(count / total_articles, 3)

        # Check exploration budget
        exp_count = current_counts.get(ContentBucket.EXPERIMENTAL.value, 0)
        actual_exp_ratio = exp_count / total_articles
        exp_exceeded = actual_exp_ratio >= max_exploration_ratio

        if exp_exceeded:
            rec = f"Exploration budget reached ({actual_exp_ratio:.1%} >= {max_exploration_ratio:.1%}). Pausing new experimental allocations."
        else:
            rec = f"Exploration allocation healthy ({actual_exp_ratio:.1%} < {max_exploration_ratio:.1%})."

        return PortfolioAllocationResult(
            target_allocations=targets,
            current_allocations=current_ratios,
            exploration_ratio=round(actual_exp_ratio, 3),
            exploration_budget_exceeded=exp_exceeded,
            can_publish_experimental=not exp_exceeded,
            recommendation=rec,
        )


class ContentInvestmentDecisionEngine:
    """Decides between refreshing an existing article, creating a new article, or doing nothing."""

    @classmethod
    def evaluate_opportunity_investment(
        cls,
        opportunity_query: str,
        opportunity_intent: str,
        opportunity_potential_clicks: int,
        matched_existing_article: dict[str, Any] | None = None,
    ) -> InvestmentDecisionResult:
        """
        Weighs existing topical authority, query overlap, update cost vs new article cost,
        and cannibalization risks to recommend the highest-ROI action (Sections 203, 274, 275).
        """
        # Case 1: No existing content anywhere near this topic
        if not matched_existing_article:
            if opportunity_potential_clicks < 50:
                return InvestmentDecisionResult(
                    choice=InvestmentChoice.DO_NOTHING,
                    refresh_score=0.0,
                    new_article_score=20.0,
                    no_action_score=80.0,
                    target_article_id=None,
                    cannibalization_risk=0.0,
                    explanation="Opportunity volume is negligible and no topical authority exists. Doing nothing.",
                )
            return InvestmentDecisionResult(
                choice=InvestmentChoice.CREATE_NEW_ARTICLE,
                refresh_score=0.0,
                new_article_score=85.0,
                no_action_score=15.0,
                target_article_id=None,
                cannibalization_risk=0.0,
                explanation="No existing content covers this intent. Standalone new article creation recommended.",
            )

        # Existing article exists: check semantic and intent overlap
        existing_title = str(matched_existing_article.get("title", ""))
        existing_intent = str(matched_existing_article.get("intent", "INFORMATIONAL"))
        existing_age_days = int(matched_existing_article.get("age_days", 60))
        existing_impressions = int(matched_existing_article.get("impressions", 1000))
        existing_id = str(matched_existing_article.get("id", matched_existing_article.get("article_id", "")))

        # Intent comparison: If intents strongly conflict (e.g. Informational vs Commercial Product Review)
        same_intent = existing_intent.lower() == opportunity_intent.lower()

        # Check cannibalization risk if we created a new article
        cannibalization_risk = 0.85 if same_intent else 0.20

        # Case 2: Strong match with same intent -> REFRESH WINS (Section 274, Test AS)
        if same_intent and existing_impressions > 200:
            refresh_score = 88.0
            new_score = 35.0  # Penalized by cannibalization risk
            no_action = 10.0

            return InvestmentDecisionResult(
                choice=InvestmentChoice.REFRESH_EXISTING,
                refresh_score=refresh_score,
                new_article_score=new_score,
                no_action_score=no_action,
                target_article_id=existing_id,
                cannibalization_risk=cannibalization_risk,
                explanation=(
                    f"Existing article '{existing_title}' already possesses established search authority "
                    f"and matches intent '{opportunity_intent}'. Refreshing existing article is more cost-effective "
                    f"and eliminates cannibalization risk."
                ),
            )

        # Case 3: Distinct intent or poor topical fit -> NEW ARTICLE WINS (Section 275, Test AT)
        refresh_score = 30.0
        new_score = 82.0
        no_action = 15.0

        return InvestmentDecisionResult(
            choice=InvestmentChoice.CREATE_NEW_ARTICLE,
            refresh_score=refresh_score,
            new_article_score=new_score,
            no_action_score=no_action,
            target_article_id=None,
            cannibalization_risk=cannibalization_risk,
            explanation=(
                f"Opportunity query '{opportunity_query}' represents distinct search intent '{opportunity_intent}' "
                f"differing from existing article '{existing_title}'. Standalone new article recommended to avoid intent dilution."
            ),
        )
