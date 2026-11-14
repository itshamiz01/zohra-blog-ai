"""
Zohra — Event Momentum Calculator.

Evaluates whether interest is accelerating, steady, or dying down:
- Combines velocity, acceleration ratio, and unique source growth
- Outputs a normalized 0–100 score.
"""

from __future__ import annotations


def calculate_momentum_score(
    velocity_score: float,
    acceleration_ratio: float,
    source_count: int,
    freshness_score: float,
) -> float:
    """
    Computes normalized Momentum Score [0.0 - 100.0].
    Higher momentum indicates sharp upward trajectory.
    """
    # 1. Base from velocity
    base = velocity_score * 0.40

    # 2. Acceleration boost
    # acceleration_ratio > 1.0 means expanding coverage
    if acceleration_ratio >= 3.0:
        accel_contrib = 30.0
    elif acceleration_ratio >= 1.5:
        accel_contrib = 20.0
    elif acceleration_ratio >= 1.0:
        accel_contrib = 10.0
    else:
        accel_contrib = acceleration_ratio * 10.0

    # 3. Source growth multiplier (independent confirmations)
    source_contrib = min(20.0, source_count * 4.0)

    # 4. Freshness multiplier
    fresh_contrib = (freshness_score / 100.0) * 10.0

    total = base + accel_contrib + source_contrib + fresh_contrib
    return min(100.0, max(0.0, round(total, 2)))


calculate_momentum = calculate_momentum_score
