"""
Zohra — Scheduling Engine & Publication Cadence Governor (Part 7).

Manages:
- Timezone conversions (IANA local site timezone to UTC).
- Publication window enforcement (e.g. 06:00-10:00, 14:00-18:00 local time).
- Daily publication limits (max_posts_per_day) preventing runaway automation.
- Minimum publish interval between consecutive articles.
- Daylight Saving Time (DST) handling via zoneinfo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.exceptions import ZohraError
from app.core.logging import get_logger

logger = get_logger("publishing.scheduler")


class SchedulingError(ZohraError):
    """Raised when publication scheduling or cadence constraints are violated."""

    def __init__(self, message: str, code: str = "SCHEDULING_ERROR"):
        super().__init__(message, code=code)


class PublicationScheduler:
    """Calculates publication slots and validates cadence limits."""

    @classmethod
    def convert_local_to_utc(cls, local_dt: datetime, timezone_str: str) -> datetime:
        """Converts naive or timezone-aware local datetime to UTC."""
        tz = ZoneInfo(timezone_str)
        if local_dt.tzinfo is None:
            localized = local_dt.replace(tzinfo=tz)
        else:
            localized = local_dt.astimezone(tz)
        return localized.astimezone(UTC)

    @classmethod
    def convert_utc_to_local(cls, utc_dt: datetime, timezone_str: str) -> datetime:
        """Converts UTC datetime to local site timezone."""
        tz = ZoneInfo(timezone_str)
        return utc_dt.astimezone(tz)

    @classmethod
    def is_within_publication_window(
        cls,
        check_dt_utc: datetime,
        timezone_str: str,
        windows: list[str] | None = None,
    ) -> bool:
        """
        Validates if target time falls within approved editorial windows (e.g. ['06:00-10:00', '14:00-18:00']).
        If windows are empty or None, all hours are allowed.
        """
        if not windows:
            return True

        local_dt = cls.convert_utc_to_local(check_dt_utc, timezone_str)
        current_time_str = local_dt.strftime("%H:%M")

        for window in windows:
            if "-" not in window:
                continue
            start_str, end_str = window.split("-", 1)
            start_str = start_str.strip()
            end_str = end_str.strip()
            if start_str <= current_time_str <= end_str:
                return True

        return False

    @classmethod
    def calculate_next_available_slot(
        cls,
        timezone_str: str,
        windows: list[str] | None,
        last_publish_time_utc: datetime | None = None,
        minimum_interval_minutes: int = 60,
    ) -> datetime:
        """
        Finds the next future UTC timestamp that satisfies minimum interval and publication windows.
        """
        now_utc = datetime.now(UTC)
        earliest_utc = now_utc + timedelta(minutes=5)  # Buffer for processing

        if last_publish_time_utc:
            min_allowed = last_publish_time_utc + timedelta(minutes=minimum_interval_minutes)
            if min_allowed > earliest_utc:
                earliest_utc = min_allowed

        # Step forward in 15-minute increments until inside an allowed window
        candidate = earliest_utc
        max_lookahead = 48 * 4  # 48 hours
        for _ in range(max_lookahead):
            if cls.is_within_publication_window(candidate, timezone_str, windows):
                return candidate
            candidate += timedelta(minutes=15)

        # Fallback to earliest if no window matched within 48h
        return earliest_utc

    @classmethod
    def validate_cadence_limits(
        cls,
        posts_published_today: int,
        max_posts_per_day: int,
        last_publish_time_utc: datetime | None,
        minimum_interval_minutes: int,
    ) -> None:
        """Enforces daily posting quotas and minimum publish spacing."""
        if posts_published_today >= max_posts_per_day:
            raise SchedulingError(
                f"Daily publication limit reached ({posts_published_today}/{max_posts_per_day} posts)",
                code="DAILY_LIMIT_EXCEEDED",
            )

        if last_publish_time_utc:
            now_utc = datetime.now(UTC)
            elapsed_minutes = (now_utc - last_publish_time_utc).total_seconds() / 60.0
            if elapsed_minutes < minimum_interval_minutes:
                raise SchedulingError(
                    f"Minimum publication interval not elapsed ({elapsed_minutes:.1f}/{minimum_interval_minutes} mins)",
                    code="MINIMUM_INTERVAL_NOT_ELAPSED",
                )
