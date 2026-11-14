"""
Zohra — Preliminary Trend Scoring & Classification.

Calculates the weighted preliminary Trend Score (0–100):
  Velocity (25%) + Momentum (20%) + Diversity (15%) + Freshness (15%)
  + Authority (10%) + Cross-Platform (10%) + Confidence (5%)

Provides:
- Trend classification labels (Noise -> Exceptional Signal)
- Human-readable trend explanation bullet points
- Part 3 qualification gatekeeper.
"""

from __future__ import annotations

from datetime import UTC

from app.core.constants import DEFAULT_TREND_WEIGHTS, TrendClassification


def classify_trend(score: float) -> TrendClassification:
    """Classifies a 0–100 trend score into an operational label."""
    if score >= 95.0:
        return TrendClassification.EXCEPTIONAL_SIGNAL
    elif score >= 85.0:
        return TrendClassification.HIGH_VELOCITY
    elif score >= 75.0:
        return TrendClassification.TRENDING
    elif score >= 65.0:
        return TrendClassification.EMERGING
    elif score >= 50.0:
        return TrendClassification.MONITOR
    elif score >= 30.0:
        return TrendClassification.WEAK_SIGNAL
    else:
        return TrendClassification.NOISE


def calculate_trend_score(
    velocity_score: float,
    momentum_score: float,
    diversity_score: float,
    freshness_score: float,
    authority_score: float,
    cross_platform_score: float = 50.0,
    confidence_score: float = 50.0,
    custom_weights: dict[str, float] | None = None,
) -> float:
    """
    Computes preliminary Trend Score [0.0 - 100.0] using configured weights.
    """
    weights = custom_weights or DEFAULT_TREND_WEIGHTS

    score = (
        (weights.get("velocity", 0.25) * velocity_score)
        + (weights.get("momentum", 0.20) * momentum_score)
        + (weights.get("diversity", 0.15) * diversity_score)
        + (weights.get("freshness", 0.15) * freshness_score)
        + (weights.get("authority", 0.10) * authority_score)
        + (weights.get("cross_platform", 0.10) * cross_platform_score)
        + (weights.get("confidence", 0.05) * confidence_score)
    )

    return min(100.0, max(0.0, round(score, 2)))


def generate_trend_reasons(
    velocity_score: float,
    momentum_score: float,
    diversity_score: float,
    freshness_score: float,
    authority_score: float,
    confidence_score: float,
    source_count: int,
    document_count: int,
    has_tier1: bool,
    acceleration_ratio: float,
    contradiction_detected: bool,
) -> list[str]:
    """
    Generates explainable, human-readable bullet points detailing why
    an event received its score.
    """
    reasons: list[str] = []

    if acceleration_ratio >= 2.0:
        reasons.append(
            f"+ High mention acceleration ({acceleration_ratio:.1f}x surge in latest window)"
        )
    elif velocity_score >= 60.0:
        reasons.append(f"+ Strong reporting velocity ({velocity_score:.1f}/100)")

    if source_count >= 3:
        reasons.append(
            f"+ Validated by {source_count} independent sources across {document_count} reports"
        )

    if has_tier1:
        reasons.append("+ Primary / official source (Tier 1) confirmation verified")

    if authority_score >= 70.0:
        reasons.append(f"+ High average source authority ({authority_score:.1f}/100)")

    if freshness_score >= 80.0:
        reasons.append("+ Breaking event: very recent publication window")

    if diversity_score >= 60.0:
        reasons.append("+ High cross-domain and geographical source diversity")

    if contradiction_detected:
        reasons.append("- Factual disagreement detected between competing sources")

    if not reasons:
        reasons.append(f"Standard baseline signal with {document_count} report(s)")

    return reasons


def is_event_qualified_for_part3(
    trend_score: float,
    confidence_score: float,
    spam_probability: float,
    status: str,
    min_trend: float = 50.0,
    min_confidence: float = 60.0,
) -> tuple[bool, str | None]:
    """
    Evaluates whether an event qualifies for Part 3 content opportunity analysis.
    Returns (is_qualified, rejection_reason_if_not).
    """
    if status in {"rejected", "archived"}:
        return False, f"Event is {status}"

    if spam_probability >= 0.50:
        return False, f"Spam probability too high ({spam_probability:.2f})"

    if trend_score < min_trend:
        return False, f"Trend score {trend_score:.1f} below handoff threshold {min_trend:.1f}"

    if confidence_score < min_confidence:
        return (
            False,
            f"Confidence score {confidence_score:.1f} below handoff threshold {min_confidence:.1f}",
        )

    return True, None


classify_trend_score = classify_trend


def calculate_event_trend(
    event: any,
    documents: list,
    sources: list,
) -> dict:
    """Computes comprehensive trend analysis across an event's documents and sources."""
    from datetime import datetime

    from app.discovery.scoring.confidence import calculate_event_confidence
    from app.discovery.scoring.diversity import calculate_source_diversity
    from app.discovery.scoring.freshness import calculate_freshness
    from app.discovery.scoring.momentum import calculate_momentum
    from app.discovery.scoring.spam import detect_event_spam
    from app.discovery.scoring.velocity import calculate_velocity_and_acceleration

    now = datetime.now(UTC)
    timestamps = [
        getattr(d, "published_at", None) or getattr(d, "discovered_at", now) for d in documents
    ]
    v_score, accel, _ = calculate_velocity_and_acceleration(timestamps, now=now)

    source_count = len(sources)
    freshness = calculate_freshness(
        first_seen=getattr(event, "first_seen_at", now),
        last_seen=getattr(event, "last_seen_at", now),
        category=getattr(event, "primary_category", "Technology"),
        now=now,
    )
    momentum = calculate_momentum(
        velocity_score=v_score,
        acceleration_ratio=accel,
        source_count=source_count,
        freshness_score=freshness,
    )
    diversity = calculate_source_diversity(sources)
    conf_res = calculate_event_confidence(documents, sources)
    confidence = conf_res["confidence_score"]

    authorities = [float(getattr(s, "authority_score", 50.0)) for s in sources]
    authority = sum(authorities) / len(authorities) if authorities else 50.0

    tiers = [
        s.tier.value if hasattr(getattr(s, "tier", None), "value") else int(getattr(s, "tier", 3))
        for s in sources
    ]
    has_tier1 = 1 in tiers

    trend_score = calculate_trend_score(
        velocity_score=v_score,
        momentum_score=momentum,
        diversity_score=diversity,
        freshness_score=freshness,
        authority_score=authority,
        confidence_score=confidence,
    )

    reasons = generate_trend_reasons(
        velocity_score=v_score,
        momentum_score=momentum,
        diversity_score=diversity,
        freshness_score=freshness,
        authority_score=authority,
        confidence_score=confidence,
        source_count=source_count,
        document_count=len(documents),
        has_tier1=has_tier1,
        acceleration_ratio=accel,
        contradiction_detected=conf_res["contradiction_detected"],
    )

    spam_res = detect_event_spam(documents, sources, accel)
    is_qual, _ = is_event_qualified_for_part3(
        trend_score=trend_score,
        confidence_score=confidence,
        spam_probability=spam_res["spam_probability"],
        status=event.status.value if hasattr(event.status, "value") else str(event.status),
    )

    return {
        "velocity_score": v_score,
        "momentum_score": momentum,
        "source_diversity_score": diversity,
        "freshness_score": freshness,
        "authority_score": authority,
        "confidence_score": confidence,
        "trend_score": trend_score,
        "classification": classify_trend(trend_score),
        "reasons": reasons,
        "is_qualified": is_qual,
    }
