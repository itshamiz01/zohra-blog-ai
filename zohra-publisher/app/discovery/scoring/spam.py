"""
Zohra — Spam Signal & Anomaly Detection.

Flags automated content farms, repetitive syndicated spam networks,
and abnormal acceleration patterns:
- High exact headline repetition across Tier 5 sources
- High keyword repetition ratio
- Assigns spam_probability [0.0 - 1.0] and ANOMALOUS_ACCELERATION flags.
"""

from __future__ import annotations

import re


def evaluate_spam_probability(
    title: str,
    content: str,
    source_tier: int,
    source_reliability: float,
    duplicate_headline_count: int = 1,
) -> float:
    """
    Computes spam probability [0.0 - 1.0] for a source document.
    """
    if not title:
        return 1.0

    score = 0.0

    # 1. Tier and source reliability baseline
    if source_tier == 5:
        score += 0.35
    elif source_tier == 4 and source_reliability < 40.0:
        score += 0.20

    # 2. Same headline repeated across multiple unverified sources
    if duplicate_headline_count >= 5 and source_tier >= 4:
        score += 0.40
    elif duplicate_headline_count >= 3 and source_tier >= 4:
        score += 0.25

    # 3. Excessive affiliate / keyword spam triggers
    content_lower = (content or "").lower()
    spam_keywords = [
        "free download",
        "click here",
        "buy cheap",
        "guaranteed prize",
        "casino",
        "gambling",
        "crypto giveaway",
        "work from home",
        "weight loss miracle",
        "exclusive discount",
    ]
    matched_spam_kw = sum(1 for kw in spam_keywords if kw in content_lower)
    if matched_spam_kw >= 3:
        score += 0.50
    elif matched_spam_kw >= 1:
        score += 0.20

    # 4. Keyword stuffing check (single word repeating more than 10% of total tokens)
    words = re.findall(r"\b\w+\b", content_lower)
    if len(words) >= 50:
        word_freq: dict[str, int] = {}
        for w in words:
            if len(w) > 4:
                word_freq[w] = word_freq.get(w, 0) + 1
        if word_freq:
            max_word_count = max(word_freq.values())
            if (max_word_count / len(words)) > 0.12:
                score += 0.30

    return min(1.0, max(0.0, round(score, 2)))


def detect_anomalous_acceleration(
    mentions_last_1h: int,
    historical_avg_per_hour: float,
    threshold_multiplier: float = 5.0,
) -> bool:
    """
    Detects if current 1-hour mention volume represents a sudden statistical spike
    over historical baseline.
    """
    if mentions_last_1h < 5:
        return False

    baseline = max(1.0, historical_avg_per_hour)
    ratio = mentions_last_1h / baseline

    return ratio >= threshold_multiplier


def detect_event_spam(
    documents: list,
    sources: list,
    velocity_acceleration: float = 1.0,
) -> dict:
    """Wrapper to evaluate spam probability across an event's documents and sources."""
    if not documents:
        return {"spam_probability": 0.0, "is_spam": False}

    probs = []
    for d, s in zip(documents, sources, strict=False):
        p = evaluate_spam_probability(
            title=getattr(d, "title", ""),
            content=getattr(d, "content_text", "")
            or getattr(d, "summary", "")
            or getattr(d, "title", ""),
            source_tier=s.tier.value
            if hasattr(getattr(s, "tier", None), "value")
            else int(getattr(s, "tier", 3)),
            source_reliability=float(getattr(s, "reliability_score", 50.0)),
            duplicate_headline_count=len(documents)
            if len({getattr(doc, "title", "") for doc in documents}) == 1
            else 1,
        )
        probs.append(p)

    avg_p = sum(probs) / len(probs)
    return {
        "spam_probability": avg_p,
        "is_spam": avg_p >= 0.50,
    }
