"""
Zohra — Event Confidence & Contradiction Detection.

Calculates confidence that the underlying event is real and consistent:
- Source reliability aggregation
- Multi-source independent confirmation
- Tier 1 official confirmation boost
- Contradiction detection across dates, numbers, and key factual statements.
"""

from __future__ import annotations

import re


def detect_contradictions(titles_and_texts: list[str]) -> tuple[bool, list[dict]]:
    """
    Scans a set of reports for direct factual contradictions:
    - Conflicting dates for an upcoming release/event
    - Conflicting money amounts for a funding/acquisition
    - Conflicting status keywords (e.g. 'cancelled' vs 'confirmed'/'released')
    """
    if len(titles_and_texts) < 2:
        return False, []

    contradictions: list[dict] = []

    # 1. Status contradiction: cancelled/delayed vs launched/confirmed
    has_cancel = any(
        re.search(r"\b(cancel|canceled|cancelled|delayed|postponed)\b", t, re.IGNORECASE)
        for t in titles_and_texts
    )
    has_launch = any(
        re.search(r"\b(launched|released|confirmed|available\s+now)\b", t, re.IGNORECASE)
        for t in titles_and_texts
    )

    if has_cancel and has_launch:
        contradictions.append(
            {
                "type": "status_disagreement",
                "description": "Reports conflict on whether the event was launched/confirmed vs delayed/cancelled.",
            }
        )

    # 2. Money discrepancies (e.g. $5B vs $10B in same cluster)
    money_mentions: set[str] = set()
    for t in titles_and_texts:
        found = re.findall(
            r"\$\s?\d+(?:,\d+)*(?:\.\d+)?\s*(?:billion|million|b|m)\b", t, re.IGNORECASE
        )
        for m in found:
            money_mentions.add(re.sub(r"\s+", "", m.lower()))

    if len(money_mentions) > 1:
        contradictions.append(
            {
                "type": "financial_discrepancy",
                "description": f"Conflicting monetary figures reported across sources: {sorted(money_mentions)}",
            }
        )

    # 3. Release date discrepancies (e.g. "October 5" vs "October 8")
    date_mentions: set[str] = set()
    for t in titles_and_texts:
        dates = re.findall(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b",
            t,
            re.IGNORECASE,
        )
        for d in dates:
            date_mentions.add(d.lower())

    if len(date_mentions) > 1:
        contradictions.append(
            {
                "type": "date_discrepancy",
                "description": f"Conflicting event dates reported across sources: {sorted(date_mentions)}",
            }
        )

    return len(contradictions) > 0, contradictions


def calculate_event_confidence_score(
    source_reliabilities: list[float],
    tiers: list[int],
    unique_domains: int,
    contradiction_detected: bool,
) -> float:
    """
    Computes Event Confidence Score [0.0 - 100.0]:
    - Average source reliability
    - Multi-domain validation bonus
    - Tier 1 presence bonus
    - Contradiction penalty
    """
    if not source_reliabilities:
        return 20.0

    avg_reliability = sum(source_reliabilities) / len(source_reliabilities)

    # Base starts at average reliability
    score = avg_reliability * 0.50

    # Multi-domain confirmation bonus (up to 30 pts)
    # 1 domain = 5pts, 2 domains = 15pts, 3+ domains = 30pts
    if unique_domains >= 3:
        score += 30.0
    elif unique_domains == 2:
        score += 15.0
    else:
        score += 5.0

    # Tier 1 official confirmation boost (up to 20 pts)
    if 1 in tiers:
        score += 20.0
    elif 2 in tiers:
        score += 10.0

    # Contradiction penalty
    if contradiction_detected:
        score = max(10.0, score - 25.0)

    return min(100.0, max(0.0, round(score, 2)))


def calculate_event_confidence(
    documents: list,
    sources: list,
) -> dict:
    """Wrapper calculating confidence score and returning dictionary with contradiction details."""
    titles_and_texts = [
        f"{getattr(d, 'title', '')} {getattr(d, 'content_text', '')}" for d in documents
    ]
    has_contradiction, notes = detect_contradictions(titles_and_texts)

    source_reliabilities = [float(getattr(s, "reliability_score", 50.0)) for s in sources]
    tiers = [
        s.tier.value if hasattr(getattr(s, "tier", None), "value") else int(getattr(s, "tier", 3))
        for s in sources
    ]
    domains = {getattr(s, "domain", "") for s in sources}
    unique_domains = len(domains - {"", None})

    conf_score = calculate_event_confidence_score(
        source_reliabilities=source_reliabilities,
        tiers=tiers,
        unique_domains=unique_domains,
        contradiction_detected=has_contradiction,
    )

    return {
        "confidence_score": conf_score,
        "contradiction_detected": has_contradiction,
        "contradiction_notes": notes,
    }
