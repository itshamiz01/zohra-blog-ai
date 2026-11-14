"""
Zohra — Event Lifecycle State Machine.

Governs event transitions based on measurable signals rather than arbitrary guesswork:
  emerging → active → accelerating → peaking → declining → stable → dormant → archived
"""

from __future__ import annotations

from app.core.constants import EventStatus


def evaluate_lifecycle_state(
    current_status: str,
    document_count: int,
    source_count: int,
    velocity_score: float,
    acceleration_ratio: float,
    freshness_score: float,
    spam_probability: float,
) -> EventStatus:
    """
    Computes next lifecycle state based on signal metrics.
    """
    # 1. Spam check
    if spam_probability >= 0.75:
        return EventStatus.REJECTED

    # 2. Terminal states check
    if current_status in {EventStatus.ARCHIVED.value, EventStatus.REJECTED.value}:
        return EventStatus(current_status)

    # 3. Dormancy / archiving check (freshness very low, no recent reports)
    if freshness_score < 10.0 and velocity_score < 5.0:
        return EventStatus.DORMANT

    # 4. Acceleration check
    if velocity_score >= 60.0 and acceleration_ratio >= 1.5:
        return EventStatus.ACCELERATING

    # 5. Peaking check (was accelerating, velocity still very high but acceleration leveling off)
    if (
        current_status == EventStatus.ACCELERATING.value
        and velocity_score >= 70.0
        and acceleration_ratio < 1.1
    ):
        return EventStatus.PEAKING

    # 6. Declining check (was peaking or accelerating, velocity dropping)
    if (
        current_status in {EventStatus.PEAKING.value, EventStatus.ACCELERATING.value}
        and velocity_score < 40.0
    ):
        return EventStatus.DECLINING

    # 7. Active check (multiple reports and sources)
    if document_count >= 2 and source_count >= 2:
        return EventStatus.ACTIVE

    # Default to emerging
    return EventStatus.EMERGING


def evaluate_event_lifecycle(event: any) -> EventStatus:
    """Convenience wrapper accepting an Event object or mock."""
    curr_status = event.status.value if hasattr(event.status, "value") else str(event.status)
    accel = getattr(
        event, "acceleration_ratio", 2.0 if getattr(event, "velocity_score", 0.0) >= 60.0 else 1.0
    )
    return evaluate_lifecycle_state(
        current_status=curr_status,
        document_count=getattr(event, "document_count", 1),
        source_count=getattr(event, "source_count", 1),
        velocity_score=getattr(event, "velocity_score", 0.0),
        acceleration_ratio=accel,
        freshness_score=getattr(event, "freshness_score", 50.0),
        spam_probability=getattr(event, "spam_probability", 0.0),
    )
