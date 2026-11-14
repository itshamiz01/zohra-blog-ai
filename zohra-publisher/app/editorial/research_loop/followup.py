"""
Zohra — Research Followup Handler (Part 5).

Handles missing critical facts discovered during drafting:
Never allows the Writer to invent or guess missing information.
Creates structured research follow-up requests routed back to Part 4.
"""

from __future__ import annotations

from typing import Any

from app.schemas.editorial import ContentStrategyData
from app.schemas.research import FinalResearchPackage


class ResearchFollowupHandler:
    """Detects essential factual gaps and generates research follow-up requests."""

    @classmethod
    def identify_missing_critical_facts(
        cls,
        research_pkg: FinalResearchPackage,
        strategy: ContentStrategyData,
    ) -> list[dict[str, Any]]:
        """Identifies if critical facts needed for the chosen content strategy are missing."""
        followups: list[dict[str, Any]] = []

        # 1. Pricing content requires pricing facts
        if strategy.recommended_content_type == "pricing":
            pricing_facts = [f for f in research_pkg.verified_facts if f.claim_type == "price" or "price" in f.claim.lower()]
            if not pricing_facts:
                followups.append({
                    "question": f"What are the official subscription tiers, currency prices, and usage limits for {research_pkg.topic}?",
                    "reason": "Draft strategy is 'pricing' but zero verified pricing facts exist in the research package.",
                    "priority": "critical",
                })

        # 2. News content requires confirmed timeline or dates
        if strategy.recommended_content_type in ("breaking_news", "news_analysis") and not research_pkg.timeline and not research_pkg.important_dates:
            followups.append({
                "question": f"What is the confirmed date and exact timeline for the recent event concerning {research_pkg.topic}?",
                "reason": "Draft strategy is news-driven but no timeline events or dates were verified in research.",
                "priority": "critical",
            })

        # 3. Check for open critical research gaps
        for gap in research_pkg.content_gaps:
            if isinstance(gap, dict) and gap.get("importance") == "critical":
                followups.append({
                    "question": gap.get("description", f"Clarification needed on {research_pkg.topic}"),
                    "reason": f"Critical research gap remains open: {gap.get('gap_type')}",
                    "priority": "critical",
                })

        return followups
