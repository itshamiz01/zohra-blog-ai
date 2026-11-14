"""
Zohra — Event Velocity & Acceleration Calculator.

Measures how fast an event is gaining reporting coverage:
- Mentions in last 15m, 1h, 6h, 24h
- Time-normalized velocity score (0–100)
- Acceleration ratio distinguishing accelerating events from declining ones.
"""

from __future__ import annotations

from datetime import UTC, datetime


def calculate_velocity_and_acceleration(
    document_timestamps: list[datetime],
    now: datetime | None = None,
) -> tuple[float, float, dict[str, int]]:
    """
    Computes (velocity_score_0_to_100, acceleration_ratio, window_counts_dict).
    """
    if not document_timestamps:
        return 0.0, 0.0, {"m15": 0, "h1": 0, "h6": 0, "h24": 0}

    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    # Sort newest to oldest
    tz_aware_ts = []
    for ts in document_timestamps:
        if ts.tzinfo is None:
            tz_aware_ts.append(ts.replace(tzinfo=UTC))
        else:
            tz_aware_ts.append(ts)

    m15_count = 0
    h1_count = 0
    h6_count = 0
    h24_count = 0

    for ts in tz_aware_ts:
        delta_sec = (current_time - ts).total_seconds()
        if delta_sec < 0:
            delta_sec = 0  # future/clock skew tolerance

        if delta_sec <= 900:  # 15 minutes
            m15_count += 1
        if delta_sec <= 3600:  # 1 hour
            h1_count += 1
        if delta_sec <= 21600:  # 6 hours
            h6_count += 1
        if delta_sec <= 86400:  # 24 hours
            h24_count += 1

    # Time-normalized velocity score
    # Rapid burst in 1h contributes heavily, sustained volume in 6h/24h adds weight
    raw_velocity = (m15_count * 25.0) + (h1_count * 15.0) + (h6_count * 4.0) + (h24_count * 1.5)
    velocity_score = min(100.0, max(0.0, round(raw_velocity, 2)))

    # Acceleration ratio: current 1h rate vs previous baseline
    # baseline = average hourly rate of remaining 5 hours (hours 2-6)
    prev_h5_count = max(0, h6_count - h1_count)
    avg_prev_hourly = prev_h5_count / 5.0

    if avg_prev_hourly > 0:
        acceleration_ratio = round(h1_count / avg_prev_hourly, 2)
    elif h1_count > 0:
        acceleration_ratio = float(h1_count)  # Sudden spike from zero
    else:
        acceleration_ratio = 0.0

    counts = {"m15": m15_count, "h1": h1_count, "h6": h6_count, "h24": h24_count}
    return velocity_score, acceleration_ratio, counts


def calculate_velocity(
    document_timestamps: list[datetime],
    now: datetime | None = None,
) -> tuple[float, float]:
    """Convenience wrapper returning (velocity_score, acceleration_ratio)."""
    v, a, _ = calculate_velocity_and_acceleration(document_timestamps, now=now)
    return v, a
