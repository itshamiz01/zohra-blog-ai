"""
Zohra — Timeline Engine.

Constructs structured chronological events with explicit temporal precision
(exact_timestamp, date, month, year, approximate, unknown) without fabricating false precision.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.schemas.research import TimelinePrecision


class BuiltTimelineEvent:
    def __init__(
        self,
        event_time: datetime | None,
        event_time_precision: TimelinePrecision,
        time_raw_text: str | None,
        description: str,
        importance: str = "major",
        source_ids: list[str] | None = None,
        confidence_score: float = 85.0,
    ):
        self.event_time = event_time
        self.event_time_precision = event_time_precision
        self.time_raw_text = time_raw_text
        self.description = description
        self.importance = importance
        self.source_ids = source_ids or []
        self.confidence_score = confidence_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "event_time_precision": self.event_time_precision.value,
            "time_raw_text": self.time_raw_text,
            "description": self.description,
            "importance": self.importance,
            "source_ids": self.source_ids,
            "confidence_score": self.confidence_score,
        }


class TimelineBuilder:
    """Builds an evidence-backed chronological sequence from extracted date/timeline claims."""

    DATE_EXACT_RE = re.compile(r"\b(202\d[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01]))\b")
    MONTH_YEAR_RE = re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(202\d)\b",
        re.I,
    )
    YEAR_RE = re.compile(r"\b(202\d)\b")
    APPROX_RE = re.compile(r"\b(?:early|mid|late|q[1-4]|summer|spring|fall|winter)\s+(202\d)\b", re.I)

    @classmethod
    def parse_temporal_precision(cls, text: str) -> tuple[datetime | None, TimelinePrecision, str | None]:
        # 1. Exact ISO or YYYY-MM-DD
        exact_m = cls.DATE_EXACT_RE.search(text)
        if exact_m:
            ds = exact_m.group(1).replace("/", "-").replace(".", "-")
            try:
                dt = datetime.fromisoformat(ds).replace(tzinfo=UTC)
                return dt, TimelinePrecision.DATE, ds
            except (ValueError, TypeError):
                pass

        # 2. Approximate phrases: "early 2026", "Q3 2026"
        approx_m = cls.APPROX_RE.search(text)
        if approx_m:
            raw = approx_m.group(0)
            return None, TimelinePrecision.APPROXIMATE, raw

        # 3. Month + Year: "October 2026"
        month_m = cls.MONTH_YEAR_RE.search(text)
        if month_m:
            month_name = month_m.group(1)
            year = int(month_m.group(2))
            raw = f"{month_name} {year}"
            try:
                dt = datetime.strptime(raw, "%B %Y").replace(tzinfo=UTC)
                return dt, TimelinePrecision.MONTH, raw
            except (ValueError, TypeError):
                pass

        # 4. Year only
        year_m = cls.YEAR_RE.search(text)
        if year_m:
            year = int(year_m.group(1))
            dt = datetime(year, 1, 1, tzinfo=UTC)
            return dt, TimelinePrecision.YEAR, str(year)

        return None, TimelinePrecision.UNKNOWN, None

    @classmethod
    def build_timeline(
        cls,
        claims: Sequence[dict[str, Any]],
    ) -> list[BuiltTimelineEvent]:
        events: list[BuiltTimelineEvent] = []

        for c in claims:
            c_text = c.get("claim_text", "")
            c_type = c.get("claim_type", "")
            eff_date = c.get("effective_date")
            t_scope = c.get("temporal_scope")
            src_id = c.get("source_id")

            # Check if this claim has timeline relevance
            if c_type in ("date", "timeline", "historical") or eff_date or t_scope:
                dt, precision, raw_str = cls.parse_temporal_precision(c_text)
                if not dt and eff_date:
                    dt = eff_date
                    precision = TimelinePrecision.DATE

                importance = "critical" if any(w in c_text.lower() for w in ("launch", "release", "announce")) else "major"

                events.append(
                    BuiltTimelineEvent(
                        event_time=dt,
                        event_time_precision=precision,
                        time_raw_text=raw_str or t_scope or "undated",
                        description=c_text,
                        importance=importance,
                        source_ids=[src_id] if src_id else [],
                        confidence_score=float(c.get("confidence_score", 85.0)),
                    )
                )

        # Sort chronological events where timestamp is present
        events.sort(key=lambda ev: ev.event_time or datetime.max.replace(tzinfo=UTC))
        return events
