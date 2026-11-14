"""Zohra — Discovery Scoring package."""

from app.discovery.scoring.confidence import calculate_event_confidence_score, detect_contradictions
from app.discovery.scoring.diversity import calculate_source_diversity_score
from app.discovery.scoring.freshness import calculate_freshness_score
from app.discovery.scoring.lifecycle import evaluate_lifecycle_state
from app.discovery.scoring.momentum import calculate_momentum_score
from app.discovery.scoring.spam import detect_anomalous_acceleration, evaluate_spam_probability
from app.discovery.scoring.trend import (
    calculate_trend_score,
    classify_trend,
    generate_trend_reasons,
    is_event_qualified_for_part3,
)
from app.discovery.scoring.velocity import calculate_velocity_and_acceleration

__all__ = [
    "calculate_velocity_and_acceleration",
    "calculate_momentum_score",
    "calculate_freshness_score",
    "calculate_source_diversity_score",
    "detect_contradictions",
    "calculate_event_confidence_score",
    "evaluate_spam_probability",
    "detect_anomalous_acceleration",
    "calculate_trend_score",
    "classify_trend",
    "generate_trend_reasons",
    "is_event_qualified_for_part3",
    "evaluate_lifecycle_state",
]
