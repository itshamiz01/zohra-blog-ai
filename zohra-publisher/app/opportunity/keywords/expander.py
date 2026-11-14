"""
Zohra — Keyword Discovery, Context-Aware Query Expansion & Normalization Engine.

Discovers search queries from Part 2 events, entities, and search signals.
Expands context-aware query families without blind template flooding.
Normalizes queries preserving distinct search intents.
Calculates internal search_demand_score without fabricating external search volume numbers.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.constants import FreshnessDecayType, SearchIntent
from app.opportunity.intent.classifier import SearchIntentClassifier


@dataclass
class KeywordCandidate:
    keyword: str
    normalized_keyword: str
    intent: SearchIntent
    secondary_intent: SearchIntent | None
    intent_confidence: float
    intent_strength_score: float
    search_demand_score: float  # Internal relative demand score (0-100)
    search_volume: int | None = None  # STRICT: NULL unless supplied by external provider
    search_volume_source: str | None = None
    search_volume_confidence: float | None = None
    competition_metric: float | None = None
    competition_source: str | None = None
    cpc: float | None = None  # STRICT: NULL unless supplied by external provider
    cpc_currency: str | None = None
    cpc_source: str | None = None
    trend_direction: str = "unknown"
    freshness_sensitivity: FreshnessDecayType = FreshnessDecayType.EVERGREEN
    commercial_value_score: float = 0.0
    provenance: dict[str, Any] = field(default_factory=dict)


class KeywordExpander:
    """Discovers, expands, normalizes, and scores keyword candidates."""

    def __init__(self) -> None:
        self.intent_classifier = SearchIntentClassifier()

    def normalize(self, query: str) -> str:
        """
        Normalizes search query without destroying intent distinction.
        - Unicode normalization (NFKC)
        - Lowercase
        - Collapse whitespace
        - Strip non-semantic punctuation, but keep vs, +, -, . in versions (e.g. 3.5, C++)
        - Preserves distinction between 'ChatGPT pricing' and 'ChatGPT API pricing'.
        """
        # Unicode normalize
        text = unicodedata.normalize("NFKC", query).strip().lower()

        # Remove redundant punctuation but preserve letters, numbers, spaces, and hyphens/pluses
        text = re.sub(r"[^\w\s\+\-\.]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        # Minor plural normalization for common generic words only (e.g. 'tutorials' -> 'tutorial', but not 'pricing')
        words = text.split()
        normalized_words = []
        for w in words:
            if w in ("tutorials", "alternatives", "reviews", "features", "tools", "models", "examples", "pricing") and w.endswith("s") and w not in ("pricing", "news"):
                w = w[:-1]
            normalized_words.append(w)

        return " ".join(normalized_words)

    def discover_and_expand(
        self,
        event_title: str,
        event_summary: str | None,
        entities: list[dict[str, Any]],
        event_type: str,
        category: str,
        trend_score: float = 50.0,
        velocity_score: float = 0.0,
        language: str = "en",
        country: str = "global",
    ) -> list[KeywordCandidate]:
        """
        Generates context-aware candidate queries from event data, entities, and semantic relationships.
        Never manufactures fake search volume or CPC numbers.
        """
        raw_candidates: set[str] = set()

        # 1. Base clean phrases from title
        clean_title = re.sub(r"[\:\-\|\–].*$", "", event_title).strip()
        raw_candidates.add(clean_title)

        # 2. Extract primary entities (products, organizations, technologies)
        product_entities: list[str] = []
        org_entities: list[str] = []

        for e in entities:
            name = e.get("name", "").strip()
            etype = e.get("type", "").lower()
            if not name or len(name) < 2:
                continue

            if etype in ("product", "technology", "software", "model", "tool"):
                product_entities.append(name)
            elif etype in ("organization", "company"):
                org_entities.append(name)
            else:
                product_entities.append(name)

        # Fallback if no structured entities: extract capitalization clusters
        if not product_entities:
            caps = re.findall(r"\b[A-Z][a-zA-Z0-9_\-\.]{2,}\b", event_title)
            product_entities = caps[:3]

        # 3. Context-aware expansion patterns based on category and event type
        is_software_or_ai = category.lower() in ("technology", "ai", "software", "business")
        is_launch_or_release = event_type in ("announcement", "launch", "release", "update")

        for entity in product_entities[:4]:
            raw_candidates.add(entity)

            # Core informational & understanding
            raw_candidates.add(f"what is {entity}")
            raw_candidates.add(f"how does {entity} work")

            # Commercial & evaluation
            raw_candidates.add(f"{entity} pricing")
            raw_candidates.add(f"{entity} review")
            raw_candidates.add(f"{entity} free vs paid")
            raw_candidates.add(f"{entity} alternatives")

            # Educational & tutorials
            raw_candidates.add(f"how to use {entity}")
            raw_candidates.add(f"{entity} tutorial for beginners")
            raw_candidates.add(f"{entity} step by step guide")

            if is_software_or_ai:
                raw_candidates.add(f"{entity} api tutorial")
                raw_candidates.add(f"{entity} features")
                raw_candidates.add(f"{entity} for youtube creators")
                raw_candidates.add(f"{entity} not working fix")

            if is_launch_or_release:
                raw_candidates.add(f"{entity} release date")
                raw_candidates.add(f"{entity} availability")

            # Comparisons with related entities or market leaders
            for other in product_entities:
                if other.lower() != entity.lower():
                    raw_candidates.add(f"{entity} vs {other}")

        # Add company + product queries
        for org in org_entities[:2]:
            for prod in product_entities[:2]:
                raw_candidates.add(f"{org} {prod}")
                raw_candidates.add(f"{org} {prod} pricing")

        # 4. Deduplicate and normalize candidates
        seen_norm: dict[str, str] = {}  # norm -> original
        for raw in raw_candidates:
            if not raw or len(raw) < 3:
                continue
            norm = self.normalize(raw)
            if norm not in seen_norm:
                seen_norm[norm] = raw

        # 5. Build structured KeywordCandidates with classified intent and internal search demand score
        results: list[KeywordCandidate] = []
        for norm, original in seen_norm.items():
            intent_res = self.intent_classifier.classify(norm)

            # Calculate internal relative search demand score (0-100)
            demand_score = self.calculate_search_demand_score(
                query=norm,
                intent=intent_res.primary_intent,
                intent_strength=intent_res.intent_strength_score,
                trend_score=trend_score,
                velocity_score=velocity_score,
            )

            # Calculate commercial value score
            commercial_val = self.calculate_commercial_value(norm, intent_res.primary_intent)

            # Determine freshness sensitivity
            freshness = self.classify_freshness_sensitivity(norm, intent_res.primary_intent)

            results.append(
                KeywordCandidate(
                    keyword=original,
                    normalized_keyword=norm,
                    intent=intent_res.primary_intent,
                    secondary_intent=intent_res.secondary_intent,
                    intent_confidence=intent_res.confidence,
                    intent_strength_score=intent_res.intent_strength_score,
                    search_demand_score=demand_score,
                    # STRICT PROVENANCE: external volume & cpc remain None
                    search_volume=None,
                    search_volume_source=None,
                    search_volume_confidence=None,
                    competition_metric=None,
                    competition_source=None,
                    cpc=None,
                    cpc_currency=None,
                    cpc_source=None,
                    trend_direction="rising" if trend_score > 60 else "stable",
                    freshness_sensitivity=freshness,
                    commercial_value_score=commercial_val,
                    provenance={
                        "discovered_from_event": event_title,
                        "generated_at": datetime.now(UTC).isoformat(),
                        "rule_engine": "ZohraKeywordExpander_v1",
                        "language": language,
                        "country": country,
                    },
                )
            )

        # Sort by internal demand score descending
        results.sort(key=lambda k: k.search_demand_score, reverse=True)
        return results

    def calculate_search_demand_score(
        self,
        query: str,
        intent: SearchIntent,
        intent_strength: float,
        trend_score: float,
        velocity_score: float,
    ) -> float:
        """
        Calculates internal search_demand_score (0.0 to 100.0).
        Merges event trend velocity, query generality/specificity balance, and search intent viability.
        Zero-volume / newly released topics are not penalized: trend velocity compensates.
        """
        # Baseline from event trend
        base_trend = trend_score * 0.40
        vel_contrib = min(20.0, velocity_score * 0.20)

        # Intent multiplier: tutorial, commercial, comparison, and clear informational
        # have sustained user search patterns
        intent_multipliers = {
            SearchIntent.TUTORIAL: 1.15,
            SearchIntent.COMMERCIAL_INVESTIGATION: 1.20,
            SearchIntent.COMPARISON: 1.18,
            SearchIntent.INFORMATIONAL: 1.00,
            SearchIntent.TROUBLESHOOTING: 1.10,
            SearchIntent.NEWS: 0.95,
            SearchIntent.NAVIGATIONAL: 0.70,  # Navigational has high clicks to official site, lower blog value
            SearchIntent.REFERENCE: 1.05,
            SearchIntent.TRANSACTIONAL: 1.10,
            SearchIntent.LOCAL: 0.80,
        }
        intent_mult = intent_multipliers.get(intent, 1.0)

        # Specificity balance (very vague queries get slightly penalized in demand utility)
        specificity_factor = (intent_strength / 100.0) * 35.0

        raw_score = (base_trend + vel_contrib + specificity_factor) * intent_mult
        return round(min(100.0, max(10.0, raw_score)), 1)

    def calculate_commercial_value(self, query: str, intent: SearchIntent) -> float:
        """Calculates commercial_value_score (0.0 to 100.0) based on buyer/decision intent."""
        if intent in (SearchIntent.COMMERCIAL_INVESTIGATION, SearchIntent.TRANSACTIONAL):
            base = 80.0
        elif intent == SearchIntent.COMPARISON:
            base = 70.0
        elif intent == SearchIntent.TUTORIAL:
            base = 45.0
        elif intent in (SearchIntent.INFORMATIONAL, SearchIntent.REFERENCE):
            base = 30.0
        else:
            base = 15.0

        q_lower = query.lower()
        if any(term in q_lower for term in ("pricing", "cost", "enterprise", "plan", "buy", "discount")):
            base += 15.0
        if any(term in q_lower for term in ("api", "b2b", "business")):
            base += 10.0

        return round(min(100.0, max(0.0, base)), 1)

    def classify_freshness_sensitivity(self, query: str, intent: SearchIntent) -> FreshnessDecayType:
        """Classifies how quickly the query's information decays."""
        q_lower = query.lower()
        if intent == SearchIntent.NEWS or any(term in q_lower for term in ("release date", "announced", "launch", "today", "breaking")):
            return FreshnessDecayType.FAST_DECAY
        if any(term in q_lower for term in ("pricing", "plans", "review", "update")):
            return FreshnessDecayType.MEDIUM_DECAY
        if intent in (SearchIntent.TUTORIAL, SearchIntent.INFORMATIONAL, SearchIntent.REFERENCE):
            return FreshnessDecayType.EVERGREEN
        return FreshnessDecayType.EVERGREEN
