"""
Zohra — AlertManager & Operational Alert Dispatcher (Part 10).

Provides:
- Deduplication key generation to eliminate alert flooding
- Cooldown throttling (groups repeated failures)
- Notification preference routing (Dashboard, Telegram, Email, Webhook)
- Alert acknowledgment, resolution, and suppression lifecycle
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import (
    Alert,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    NotificationLog,
    NotificationPreference,
)
from app.services.notifications import (
    get_notification_provider,
    is_within_quiet_hours,
)


class AlertManager:
    """Central engine managing operational alerts and external notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_deduplication_key(
        self,
        site_id: uuid.UUID | None,
        category: str,
        source: str,
        entity_type: str | None,
        entity_id: str | None,
        title: str,
    ) -> str:
        """Create deterministic SHA-256 fingerprint for deduplicating repeated alerts."""
        raw = f"{site_id or 'global'}:{category}:{source}:{entity_type or ''}:{entity_id or ''}:{title}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def emit_alert(
        self,
        title: str,
        message: str,
        category: AlertCategory | str = AlertCategory.SYSTEM,
        severity: AlertSeverity | str = AlertSeverity.WARNING,
        source: str = "system",
        site_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        cooldown_minutes: int = 15,
    ) -> Alert:
        """
        Record operational alert.
        If a duplicate open alert exists within cooldown_minutes, aggregates the count
        instead of spamming external notification channels.
        """
        cat_val = category.value if isinstance(category, AlertCategory) else str(category)
        sev_val = severity.value if isinstance(severity, AlertSeverity) else str(severity)
        dedup_key = self.generate_deduplication_key(
            site_id, cat_val, source, entity_type, entity_id, title
        )

        cutoff = datetime.now(UTC) - timedelta(minutes=cooldown_minutes)

        # Check for active existing alert with same deduplication key
        query = (
            select(Alert)
            .where(
                Alert.deduplication_key == dedup_key,
                Alert.status.in_([AlertStatus.OPEN.value, AlertStatus.ACKNOWLEDGED.value]),
                Alert.created_at >= cutoff,
            )
            .order_by(desc(Alert.created_at))
            .limit(1)
        )
        res = await self.db.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.occurrence_count += 1
            if metadata:
                existing.metadata_json = {**existing.metadata_json, **metadata}
            await self.db.flush()
            return existing

        # Create brand new alert
        new_alert = Alert(
            site_id=site_id,
            category=cat_val,
            severity=sev_val,
            title=title,
            message=message,
            source=source,
            entity_type=entity_type,
            entity_id=entity_id,
            status=AlertStatus.OPEN.value,
            deduplication_key=dedup_key,
            occurrence_count=1,
            metadata_json=metadata or {},
        )
        self.db.add(new_alert)
        await self.db.flush()

        # Route notifications
        await self._dispatch_notifications(new_alert)
        return new_alert

    async def _dispatch_notifications(self, alert: Alert) -> None:
        """Evaluate preferences and deliver notifications across configured channels."""
        # Find matching preferences
        pref_query = select(NotificationPreference).where(
            (NotificationPreference.site_id == alert.site_id)
            | (NotificationPreference.site_id.is_(None))
        )
        pref_res = await self.db.execute(pref_query)
        preferences = pref_res.scalars().all()

        channels = {"DASHBOARD"}
        now_time = datetime.now(UTC).time()

        for pref in preferences:
            # Check quiet hours unless critical override allowed
            in_quiet = is_within_quiet_hours(
                now_time, pref.quiet_hours_start, pref.quiet_hours_end
            )
            if in_quiet and not (alert.severity == AlertSeverity.CRITICAL.value and pref.allow_critical_override):
                continue

            for ch in pref.channels_json:
                channels.add(ch)

        for channel in channels:
            provider = get_notification_provider(channel)
            recipient_ref = "dashboard" if channel == "DASHBOARD" else "configured_recipient"
            success, error_msg = await provider.send(alert, recipient_ref)

            log_entry = NotificationLog(
                alert_id=alert.id,
                channel=channel,
                recipient_ref=recipient_ref,
                status="SENT" if success else "FAILED",
                attempts=1,
                failure_reason=error_msg,
                sent_at=datetime.now(UTC),
            )
            self.db.add(log_entry)

        await self.db.flush()

    async def acknowledge_alert(self, alert_id: uuid.UUID, user_ref: str) -> Alert | None:
        """Mark alert as acknowledged."""
        query = select(Alert).where(Alert.id == alert_id)
        res = await self.db.execute(query)
        alert = res.scalar_one_or_none()
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED.value
            alert.acknowledged_at = datetime.now(UTC)
            alert.acknowledged_by = user_ref
            await self.db.flush()
        return alert

    async def resolve_alert(self, alert_id: uuid.UUID, user_ref: str) -> Alert | None:
        """Mark alert as resolved."""
        query = select(Alert).where(Alert.id == alert_id)
        res = await self.db.execute(query)
        alert = res.scalar_one_or_none()
        if alert:
            alert.status = AlertStatus.RESOLVED.value
            alert.resolved_at = datetime.now(UTC)
            alert.resolved_by = user_ref
            await self.db.flush()
        return alert

    async def get_active_alerts(
        self,
        site_id: uuid.UUID | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[Alert]:
        """Fetch unresolved alerts for dashboard display."""
        query = select(Alert).where(
            Alert.status.in_([AlertStatus.OPEN.value, AlertStatus.ACKNOWLEDGED.value])
        )
        if site_id:
            query = query.where(Alert.site_id == site_id)
        if severity:
            query = query.where(Alert.severity == severity)

        query = query.order_by(desc(Alert.created_at)).limit(limit)
        res = await self.db.execute(query)
        return list(res.scalars().all())
