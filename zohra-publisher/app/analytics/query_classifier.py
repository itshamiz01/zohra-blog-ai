"""
Zohra — Query Normalizer & Intent Classifier (Part 8).

Provides:
- Query text normalization (lowercase, whitespace collapse, stopword-aware)
- Deterministic search intent classification
- Brand query detection
- Query word-count stats
"""

from __future__ import annotations

import re

from app.schemas.analytics import QueryClassificationResult, SearchIntent

# Known commercial/transactional modifiers
_TRANSACTIONAL_MODIFIERS = frozenset({
    "buy", "purchase", "order", "price", "pricing", "cost", "cheap",
    "deal", "discount", "coupon", "sale", "subscribe", "download",
    "free trial", "sign up", "get",
})

_COMMERCIAL_MODIFIERS = frozenset({
    "best", "top", "review", "reviews", "comparison", "vs", "versus",
    "alternative", "alternatives", "compare", "rated", "recommended",
})

_INFORMATIONAL_MODIFIERS = frozenset({
    "how", "what", "why", "when", "where", "which", "who",
    "guide", "tutorial", "tips", "learn", "examples", "definition",
    "meaning", "explain", "explained", "overview",
})

_LOCAL_MODIFIERS = frozenset({
    "near me", "nearby", "near", "local", "directions", "location",
    "hours", "open now", "closest",
})

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALPHANUMERIC = re.compile(r"[^\w\s\-]", re.UNICODE)


def normalize_query(query: str) -> str:
    """Normalize a search query for consistent matching.

    Rules:
    - Lowercase
    - Collapse whitespace
    - Strip leading/trailing whitespace
    - Preserve hyphens (common in SEO terms)
    - Remove other punctuation
    """
    q = query.lower().strip()
    q = _NON_ALPHANUMERIC.sub("", q)
    q = _WHITESPACE_RE.sub(" ", q).strip()
    return q


def classify_intent(query: str) -> SearchIntent:
    """Classify search intent from query text.

    Uses modifier-based heuristics. Falls back to INFORMATIONAL.
    """
    q = query.lower().strip()
    words = set(q.split())

    # Check local first (can overlap)
    for mod in _LOCAL_MODIFIERS:
        if mod in q:
            return SearchIntent.LOCAL

    # Transactional
    if words & _TRANSACTIONAL_MODIFIERS:
        return SearchIntent.TRANSACTIONAL

    # Commercial investigation
    if words & _COMMERCIAL_MODIFIERS:
        return SearchIntent.COMMERCIAL

    # Informational question patterns
    if words & _INFORMATIONAL_MODIFIERS:
        return SearchIntent.INFORMATIONAL

    # Navigational heuristic: very short (1-2 words), likely a brand/nav
    if len(words) <= 2 and not words & _INFORMATIONAL_MODIFIERS:
        return SearchIntent.NAVIGATIONAL

    return SearchIntent.INFORMATIONAL


def is_branded_query(query: str, brand_terms: list[str] | None = None) -> bool:
    """Check if a query contains brand terms."""
    if not brand_terms:
        return False
    q = query.lower()
    return any(term.lower() in q for term in brand_terms)


def classify_query(
    query: str,
    brand_terms: list[str] | None = None,
) -> QueryClassificationResult:
    """Full classification pipeline for a single query."""
    normalized = normalize_query(query)
    intent = classify_intent(normalized)
    branded = is_branded_query(normalized, brand_terms)
    word_count = len(normalized.split()) if normalized else 0

    return QueryClassificationResult(
        query=query,
        normalized_query=normalized,
        intent=intent,
        confidence=0.7 if intent != SearchIntent.INFORMATIONAL else 0.5,
        is_branded=branded,
        word_count=word_count,
    )
