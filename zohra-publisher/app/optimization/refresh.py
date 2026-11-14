"""
Zohra — Part 9 Content Refresh Engine.

Implements Sections 23 to 30, 207 to 216 of Part 9 Master Prompt:
- Formula-driven Refresh Score:
    Score = Traffic Loss Potential × Recoverable Search Opportunity × Business Importance × Freshness Need × Evidence Confidence
- Priority bands (0-39 NO_ACTION, 40-59 WATCH, 60-74 REFRESH_CANDIDATE, 75-89 HIGH_PRIORITY_REFRESH, 90-100 URGENT_REVIEW)
- Stale claim detection from Part 4/6 evidence records
- Date-sensitive year transition detection (e.g., '2026', 'current')
- Integration handoff: Part 9 -> Part 4 Research -> Part 5 Drafting -> Part 6 Verification -> Part 7 Publication
- Refresh fatigue prevention (penalizes repeated unrewarded refreshes)
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from datetime import UTC
from enum import Enum
from typing import Any


class RefreshPriority(str, Enum):
    NO_ACTION = "NO_ACTION"
    WATCH = "WATCH"
    REFRESH_CANDIDATE = "REFRESH_CANDIDATE"
    HIGH_PRIORITY_REFRESH = "HIGH_PRIORITY_REFRESH"
    URGENT_REVIEW = "URGENT_REVIEW"


class RefreshType(str, Enum):
    FACTUAL_UPDATE = "FACTUAL_UPDATE"
    STATISTICS_UPDATE = "STATISTICS_UPDATE"
    PRODUCT_UPDATE = "PRODUCT_UPDATE"
    NEWS_UPDATE = "NEWS_UPDATE"
    CONTENT_EXPANSION = "CONTENT_EXPANSION"
    CONTENT_PRUNING = "CONTENT_PRUNING"
    SEARCH_INTENT_REALIGNMENT = "SEARCH_INTENT_REALIGNMENT"
    QUERY_EXPANSION = "QUERY_EXPANSION"
    FAQ_UPDATE = "FAQ_UPDATE"
    STRUCTURAL_REFRESH = "STRUCTURAL_REFRESH"
    TITLE_REFRESH = "TITLE_REFRESH"
    META_REFRESH = "META_REFRESH"
    INTERNAL_LINK_REFRESH = "INTERNAL_LINK_REFRESH"
    MEDIA_REFRESH = "MEDIA_REFRESH"
    FULL_REFRESH = "FULL_REFRESH"


@dataclass
class StaleClaimItem:
    claim_id: str
    statement: str
    evidence_age_days: int
    is_time_sensitive: bool
    source_url: str | None = None


@dataclass
class RefreshEvaluation:
    refresh_score: float
    priority: RefreshPriority
    recommended_refresh_types: list[RefreshType]
    stale_claims: list[StaleClaimItem] = field(default_factory=list)
    date_sensitive_tokens: list[str] = field(default_factory=list)
    requires_research: bool = False
    requires_verification: bool = False
    fatigue_penalty_applied: bool = False
    explanation: str = ""


class ContentRefreshEngine:
    """Evaluates content staleness, calculates priority score, and constructs refresh plans."""

    @classmethod
    def calculate_refresh_score(
        cls,
        traffic_loss_potential: float,          # 0.0 - 1.0 (e.g. percent traffic dropped)
        recoverable_search_opportunity: float,  # 0.0 - 1.0 (e.g. impression volume on lost queries)
        business_importance: float,             # 0.0 - 1.0 (commercial value / priority tier)
        freshness_need: float,                  # 0.0 - 1.0 (stale claims, age, year in title)
        evidence_confidence: float,             # 0.0 - 1.0 (statistical certainty in decay)
        previous_failed_refreshes: int = 0,     # Fatigue counter
    ) -> tuple[float, RefreshPriority, bool]:
        """
        Calculates normalized 0-100 Refresh Score.
        Formula:
            Score = (Traffic Loss × Recoverable Opp × Business Importance × Freshness Need × Evidence Confidence)
        Normalized and scaled with fatigue damping.
        """
        # Clamp inputs to [0.0, 1.0]
        tl = min(1.0, max(0.0, traffic_loss_potential))
        ro = min(1.0, max(0.0, recoverable_search_opportunity))
        bi = min(1.0, max(0.0, business_importance))
        fn = min(1.0, max(0.0, freshness_need))
        ec = min(1.0, max(0.0, evidence_confidence))

        # Geometric/weighted calculation:
        # Base product:
        raw_product = (tl ** 0.6) * (ro ** 0.5) * (bi ** 0.4) * (fn ** 0.7) * (ec ** 0.5)
        score = raw_product * 100.0

        # Apply fatigue damping (Section 215):
        fatigue_applied = False
        if previous_failed_refreshes > 0:
            fatigue_penalty = min(0.50, 0.15 * previous_failed_refreshes)
            score *= (1.0 - fatigue_penalty)
            fatigue_applied = True

        score = round(min(100.0, max(0.0, score)), 1)

        # Map to priority bands (Section 25)
        if score >= 90.0:
            priority = RefreshPriority.URGENT_REVIEW
        elif score >= 75.0:
            priority = RefreshPriority.HIGH_PRIORITY_REFRESH
        elif score >= 60.0:
            priority = RefreshPriority.REFRESH_CANDIDATE
        elif score >= 40.0:
            priority = RefreshPriority.WATCH
        else:
            priority = RefreshPriority.NO_ACTION

        return score, priority, fatigue_applied

    @classmethod
    def detect_stale_claims(
        cls,
        claims: list[dict[str, Any]],
        max_staleness_days: int = 90,
    ) -> list[StaleClaimItem]:
        """
        Scans Part 4/6 claims for time-sensitive statements whose evidence has aged out.
        """
        stale_items: list[StaleClaimItem] = []
        now = datetime.datetime.now(UTC)

        for c in claims:
            time_sensitive = c.get("time_sensitive", False) or c.get("is_time_sensitive", False)
            evidence_date = c.get("verified_at") or c.get("created_at") or c.get("evidence_date")

            age_days = 0
            if isinstance(evidence_date, str):
                try:
                    dt = datetime.datetime.fromisoformat(evidence_date.replace("Z", "+00:00"))
                    age_days = (now - dt).days
                except (ValueError, TypeError):
                    age_days = 91
            elif isinstance(evidence_date, datetime.datetime):
                dt = evidence_date if evidence_date.tzinfo else evidence_date.replace(tzinfo=UTC)
                age_days = (now - dt).days

            # Time sensitive claims expire faster (e.g. 60 days vs 180 days)
            threshold = (max_staleness_days // 2) if time_sensitive else max_staleness_days

            if age_days > threshold:
                stale_items.append(
                    StaleClaimItem(
                        claim_id=str(c.get("id", c.get("claim_id", ""))),
                        statement=str(c.get("claim_text", c.get("statement", ""))),
                        evidence_age_days=age_days,
                        is_time_sensitive=time_sensitive,
                        source_url=c.get("source_url"),
                    )
                )

        return stale_items

    @classmethod
    def detect_date_sensitive_tokens(cls, title: str, body: str) -> list[str]:
        """
        Identifies date/year tokens that signal imminent staleness (Section 209).
        """
        current_year = datetime.datetime.now(UTC).year
        candidates = [
            str(current_year - 1),
            str(current_year),
            str(current_year + 1),
            "latest",
            "current",
            "this year",
            "today",
            "updated",
        ]
        found: list[str] = []
        combined = f"{title.lower()} {body[:1000].lower()}"

        for cand in candidates:
            if re.search(r"\b" + re.escape(cand) + r"\b", combined):
                found.append(cand)

        return found

    @classmethod
    def evaluate_article_for_refresh(
        cls,
        article_title: str,
        article_body: str,
        claims: list[dict[str, Any]],
        performance_signals: dict[str, Any],
        business_importance: float = 0.7,
        lifetime_refreshes: int = 0,
        unsuccessful_refreshes: int = 0,
        max_staleness_days: int = 90,
    ) -> RefreshEvaluation:
        """
        Complete refresh evaluation workflow combining decay metrics, stale claims, and date tokens.
        """
        traffic_loss = float(performance_signals.get("traffic_loss_pct", 0.0))
        recoverable_opp = float(performance_signals.get("recoverable_opportunity_pct", 0.5))
        evidence_conf = float(performance_signals.get("confidence", 0.8))

        stale_claims = cls.detect_stale_claims(claims, max_staleness_days=max_staleness_days)
        date_tokens = cls.detect_date_sensitive_tokens(article_title, article_body)

        # Freshness need factor
        freshness_need = 0.2
        if stale_claims:
            freshness_need += min(0.5, len(stale_claims) * 0.15)
        if date_tokens:
            freshness_need += 0.3
        freshness_need = min(1.0, freshness_need)

        score, priority, fatigue_applied = cls.calculate_refresh_score(
            traffic_loss_potential=traffic_loss,
            recoverable_search_opportunity=recoverable_opp,
            business_importance=business_importance,
            freshness_need=freshness_need,
            evidence_confidence=evidence_conf,
            previous_failed_refreshes=unsuccessful_refreshes,
        )

        # Identify required refresh types
        rec_types: list[RefreshType] = []
        requires_research = False
        requires_verification = False

        if stale_claims:
            rec_types.append(RefreshType.FACTUAL_UPDATE)
            rec_types.append(RefreshType.STATISTICS_UPDATE)
            requires_research = True
            requires_verification = True

        if date_tokens:
            rec_types.append(RefreshType.TITLE_REFRESH)
            rec_types.append(RefreshType.META_REFRESH)

        if performance_signals.get("has_query_expansion"):
            rec_types.append(RefreshType.QUERY_EXPANSION)
            rec_types.append(RefreshType.CONTENT_EXPANSION)

        if not rec_types:
            rec_types.append(RefreshType.STRUCTURAL_REFRESH)

        explanation = (
            f"Calculated Refresh Score: {score}/100 ({priority.value}). "
            f"Stale claims: {len(stale_claims)}, Date tokens: {date_tokens}."
        )
        if fatigue_applied:
            explanation += f" Fatigue damping applied due to {unsuccessful_refreshes} previous unrewarded refreshes."

        return RefreshEvaluation(
            refresh_score=score,
            priority=priority,
            recommended_refresh_types=rec_types,
            stale_claims=stale_claims,
            date_sensitive_tokens=date_tokens,
            requires_research=requires_research,
            requires_verification=requires_verification,
            fatigue_penalty_applied=fatigue_applied,
            explanation=explanation,
        )
