"""
Zohra — Content Angle Generation & Audience Fit Engine.

Transforms trending events into diverse, non-redundant content angles
(e.g., breaking news, beginner explainer, practical tutorial, commercial pricing,
comparison matrix, developer API walkthrough).
Maps angles to specific target audiences and content types with fit scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.constants import ClusterRole, ContentType, FreshnessDecayType, SearchIntent


@dataclass
class ProposedAngle:
    proposed_angle: str
    working_title: str
    content_type: ContentType
    primary_intent: SearchIntent
    secondary_intent: SearchIntent | None
    target_audience: list[str]
    cluster_role: ClusterRole
    content_type_fit_score: float  # 0 to 100
    audience_fit_score: float  # 0 to 100
    freshness_decay_type: FreshnessDecayType
    evergreen_score: float  # 0 to 100
    freshness_score: float  # 0 to 100
    scoring_profile: str  # breaking_news, evergreen, commercial_comparison, default
    rationale: str


class AngleGenerator:
    """Generates distinct, diverse publishing angles for an event/topic."""

    def generate_angles(
        self,
        canonical_topic: str,
        event_title: str,
        category: str,
        entities: list[dict[str, Any]],
        trend_score: float = 50.0,
        site_audiences: list[str] | None = None,
    ) -> list[ProposedAngle]:
        angles: list[ProposedAngle] = []
        clean_entity = entities[0].get("name", canonical_topic) if entities else canonical_topic

        site_auds = site_audiences or ["tech enthusiasts", "professionals", "creators"]

        # Angle 1: Breaking News / Analysis (Fast decay, high immediate freshness)
        if trend_score >= 60.0:
            angles.append(
                ProposedAngle(
                    proposed_angle="Timely Launch & News Analysis",
                    working_title=f"{clean_entity} Announced: Key Features, Release Date & What It Means",
                    content_type=ContentType.BREAKING_NEWS,
                    primary_intent=SearchIntent.NEWS,
                    secondary_intent=SearchIntent.INFORMATIONAL,
                    target_audience=site_auds[:2],
                    cluster_role=ClusterRole.NEWS,
                    content_type_fit_score=95.0,
                    audience_fit_score=90.0,
                    freshness_decay_type=FreshnessDecayType.FAST_DECAY,
                    evergreen_score=25.0,
                    freshness_score=95.0,
                    scoring_profile="breaking_news",
                    rationale="Captures immediate surge traffic from announcement with quick-turnaround overview.",
                )
            )

        # Angle 2: Practical Tutorial / Workflow (Evergreen, high search utility)
        angles.append(
            ProposedAngle(
                proposed_angle="Hands-on Practical Tutorial",
                working_title=f"How to Use {clean_entity}: Step-by-Step Beginner's Guide",
                content_type=ContentType.TUTORIAL,
                primary_intent=SearchIntent.TUTORIAL,
                secondary_intent=SearchIntent.INFORMATIONAL,
                target_audience=["beginners", "creators", "power users"],
                cluster_role=ClusterRole.SUPPORTING,
                content_type_fit_score=92.0,
                audience_fit_score=92.0,
                freshness_decay_type=FreshnessDecayType.EVERGREEN,
                evergreen_score=88.0,
                freshness_score=60.0,
                scoring_profile="evergreen",
                rationale="Solves actionable implementation demand. High long-tail evergreen value.",
            )
        )

        # Angle 3: Commercial & Pricing Breakdown (High commercial intent)
        angles.append(
            ProposedAngle(
                proposed_angle="Transparent Pricing & Value Breakdown",
                working_title=f"{clean_entity} Pricing Explained: Free Plan, Tiers & Is It Worth It?",
                content_type=ContentType.PRICING,
                primary_intent=SearchIntent.COMMERCIAL_INVESTIGATION,
                secondary_intent=SearchIntent.TRANSACTIONAL,
                target_audience=["buyers", "business owners", "creators"],
                cluster_role=ClusterRole.SUPPORTING,
                content_type_fit_score=90.0,
                audience_fit_score=85.0,
                freshness_decay_type=FreshnessDecayType.MEDIUM_DECAY,
                evergreen_score=75.0,
                freshness_score=70.0,
                scoring_profile="commercial_comparison",
                rationale="Targeting decision-stage users evaluating costs and free tier limitations.",
            )
        )

        # Angle 4: Comparison vs Market Alternatives
        comp_target = entities[1].get("name", "Top Alternatives") if len(entities) > 1 else "Market Leaders"
        angles.append(
            ProposedAngle(
                proposed_angle="Head-to-Head Comparative Benchmark",
                working_title=f"{clean_entity} vs {comp_target}: Features, Speed & Benchmark Comparison",
                content_type=ContentType.COMPARISON,
                primary_intent=SearchIntent.COMPARISON,
                secondary_intent=SearchIntent.COMMERCIAL_INVESTIGATION,
                target_audience=["evaluators", "power users", "decision makers"],
                cluster_role=ClusterRole.SUPPORTING,
                content_type_fit_score=94.0,
                audience_fit_score=88.0,
                freshness_decay_type=FreshnessDecayType.MEDIUM_DECAY,
                evergreen_score=80.0,
                freshness_score=65.0,
                scoring_profile="commercial_comparison",
                rationale="High commercial intent comparison matrix answering which tool performs better.",
            )
        )

        # Angle 5: Pillar / Comprehensive Explainer Guide
        angles.append(
            ProposedAngle(
                proposed_angle="Comprehensive Architectural Explainer",
                working_title=f"What is {clean_entity}? Complete Architectural Deep Dive & Guide",
                content_type=ContentType.EXPLAINER,
                primary_intent=SearchIntent.INFORMATIONAL,
                secondary_intent=SearchIntent.REFERENCE,
                target_audience=site_auds,
                cluster_role=ClusterRole.PILLAR,
                content_type_fit_score=88.0,
                audience_fit_score=85.0,
                freshness_decay_type=FreshnessDecayType.EVERGREEN,
                evergreen_score=90.0,
                freshness_score=55.0,
                scoring_profile="evergreen",
                rationale="Acts as the topical pillar for internal link clustering and broad authority.",
            )
        )

        # Angle 6: Specific Creator or Developer Use Case
        angles.append(
            ProposedAngle(
                proposed_angle="Niche Creator Automation Workflow",
                working_title=f"{clean_entity} for YouTube Creators: Complete Production Workflow",
                content_type=ContentType.GUIDE,
                primary_intent=SearchIntent.TUTORIAL,
                secondary_intent=SearchIntent.INFORMATIONAL,
                target_audience=["YouTube creators", "video editors", "marketers"],
                cluster_role=ClusterRole.SUPPORTING,
                content_type_fit_score=91.0,
                audience_fit_score=95.0,
                freshness_decay_type=FreshnessDecayType.EVERGREEN,
                evergreen_score=85.0,
                freshness_score=65.0,
                scoring_profile="evergreen",
                rationale="Highly specific audience angle with low competition and clear information gain.",
            )
        )

        return angles
