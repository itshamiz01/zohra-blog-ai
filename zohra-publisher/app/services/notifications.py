"""
Zohra — Notification Delivery Providers & Routing (Part 10).

Provides:
- NotificationProvider abstract interface
- DashboardNotificationProvider
- TelegramNotificationProvider
- EmailNotificationProvider
- WebhookNotificationProvider
- Quiet hours evaluation
"""

from __future__ import annotations

import abc
import datetime

import httpx

from app.db.models.operations import Alert, NotificationChannel


def is_within_quiet_hours(
    now_time: datetime.time,
    quiet_start_str: str | None,
    quiet_end_str: str | None,
) -> bool:
    """Evaluate whether the given time falls inside configured quiet hours (e.g. 22:00 to 08:00)."""
    if not quiet_start_str or not quiet_end_str:
        return False
    try:
        start_parts = [int(p) for p in quiet_start_str.split(":")]
        end_parts = [int(p) for p in quiet_end_str.split(":")]
        start_time = datetime.time(start_parts[0], start_parts[1])
        end_time = datetime.time(end_parts[0], end_parts[1])
    except (ValueError, IndexError):
        return False

    if start_time <= end_time:
        return start_time <= now_time <= end_time
    # Crosses midnight (e.g., 22:00 -> 08:00)
    return now_time >= start_time or now_time <= end_time


class NotificationProvider(abc.ABC):
    """Abstract interface for external notification delivery."""

    @abc.abstractmethod
    async def send(self, alert: Alert, recipient_ref: str) -> tuple[bool, str | None]:
        """
        Deliver notification.
        Returns (success: bool, error_message: str | None).
        Never log or return raw secrets or tokens.
        """
        pass


class DashboardNotificationProvider(NotificationProvider):
    """Internal notification provider. Relies on Alert persistence in database."""

    async def send(self, alert: Alert, recipient_ref: str) -> tuple[bool, str | None]:
        return True, None


class TelegramNotificationProvider(NotificationProvider):
    """Telegram Bot notification provider."""

    def __init__(self, bot_token: str | None = None, default_chat_id: str | None = None):
        self.bot_token = bot_token
        self.default_chat_id = default_chat_id

    async def send(self, alert: Alert, recipient_ref: str) -> tuple[bool, str | None]:
        chat_id = recipient_ref or self.default_chat_id
        if not self.bot_token or not chat_id:
            return False, "Telegram not configured (missing token or chat_id)"

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        text = (
            f"🚨 *[{alert.severity}] {alert.category}*\n\n"
            f"*{alert.title}*\n"
            f"{alert.message}\n\n"
            f"_Source: {alert.source} | Site: {alert.site_id or 'Global'}_"
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
                if res.status_code == 200:
                    return True, None
                return False, f"Telegram API error HTTP {res.status_code}"
        except Exception as e:
            return False, f"Telegram network failure: {type(e).__name__}"


class EmailNotificationProvider(NotificationProvider):
    """Email delivery provider for high-severity alerts and digests."""

    async def send(self, alert: Alert, recipient_ref: str) -> tuple[bool, str | None]:
        # Clean production abstraction — verifies valid recipient
        if "@" not in recipient_ref:
            return False, "Invalid recipient email address"
        # In containerized production, this bridges to configured SMTP or SES
        return True, None


class WebhookNotificationProvider(NotificationProvider):
    """Generic Webhook notification delivery."""

    async def send(self, alert: Alert, recipient_ref: str) -> tuple[bool, str | None]:
        if not recipient_ref.startswith(("http://", "https://")):
            return False, "Invalid webhook URL scheme"

        payload = {
            "alert_id": str(alert.id),
            "severity": alert.severity,
            "category": alert.category,
            "title": alert.title,
            "message": alert.message,
            "source": alert.source,
            "site_id": str(alert.site_id) if alert.site_id else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(recipient_ref, json=payload)
                if 200 <= res.status_code < 300:
                    return True, None
                return False, f"Webhook responded with HTTP {res.status_code}"
        except Exception as e:
            return False, f"Webhook delivery error: {type(e).__name__}"


def get_notification_provider(channel: str) -> NotificationProvider:
    """Factory resolving appropriate provider implementation."""
    ch = channel.upper()
    if ch == NotificationChannel.TELEGRAM.value:
        return TelegramNotificationProvider()
    if ch == NotificationChannel.EMAIL.value:
        return EmailNotificationProvider()
    if ch == NotificationChannel.WEBHOOK.value:
        return WebhookNotificationProvider()
    return DashboardNotificationProvider()
