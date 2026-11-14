"""
Zohra — Part 9 Performance Forecasting & Seasonality Intelligence.

Implements Sections 110, 111, 116 to 120 of Part 9 Master Prompt:
- Conservative statistical performance ranges (low, mid, high) with explicit uncertainty disclosure
- Seasonality model tracking recurring cyclical peaks and troughs by topic/niche
- Trend lifecycle classification: FLASH, SHORT_LIVED, SEASONAL, SUSTAINED, EVERGREEN_TRANSITION
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class TrendLifecycleClass(str, Enum):
    FLASH = "FLASH"                               # Rapid spike lasting < 72 hours
    SHORT_LIVED = "SHORT_LIVED"                   # 1-3 weeks interest window
    SEASONAL = "SEASONAL"                         # Annual recurring cycle
    SUSTAINED = "SUSTAINED"                       # Steady ongoing search volume
    EVERGREEN_TRANSITION = "EVERGREEN_TRANSITION" # Trend converting to permanent reference


@dataclass
class ForecastRange:
    low: int
    mid: int
    high: int


@dataclass
class PerformanceForecast:
    article_id: str
    window: str
    metric: str
    expected_range: ForecastRange
    confidence: float
    methodology: str = "conservative_rolling_historical_bounds"

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "window": self.window,
            "metric": self.metric,
            "expected_range": asdict(self.expected_range),
            "confidence": self.confidence,
            "methodology": self.methodology,
        }


@dataclass
class SeasonalPattern:
    topic: str
    start_month: int  # 1-12
    peak_month: int   # 1-12
    decline_month: int
    historical_years_observed: int
    confidence: float


class PerformanceForecastService:
    """Computes bounded statistical performance ranges without false precision."""

    @classmethod
    def forecast_metric_range(
        cls,
        article_id: str,
        metric: str,
        recent_daily_values: list[float],
        forecast_days: int = 28,
    ) -> PerformanceForecast:
        """
        Produces conservative low/mid/high range estimate with explicit uncertainty.
        """
        if not recent_daily_values:
            return PerformanceForecast(
                article_id=article_id,
                window=f"next_{forecast_days}d",
                metric=metric,
                expected_range=ForecastRange(low=0, mid=0, high=0),
                confidence=0.20,
            )

        n = len(recent_daily_values)
        avg_daily = sum(recent_daily_values) / n
        expected_mid = round(avg_daily * forecast_days)

        # Standard deviation for variance bounds
        variance = sum((x - avg_daily) ** 2 for x in recent_daily_values) / max(1, n - 1)
        std_dev = math.sqrt(variance)

        margin = std_dev * math.sqrt(forecast_days) * 1.5
        expected_low = max(0, round(expected_mid - margin))
        expected_high = round(expected_mid + margin)

        # Confidence scales with observation history length
        confidence = min(0.85, 0.40 + (0.015 * min(n, 30)))

        return PerformanceForecast(
            article_id=article_id,
            window=f"next_{forecast_days}d",
            metric=metric,
            expected_range=ForecastRange(low=expected_low, mid=expected_mid, high=expected_high),
            confidence=round(confidence, 2),
        )


class SeasonalityModel:
    """Maintains empirical annual seasonality curves for recurring topics."""

    KNOWN_PATTERNS = {
        "tax": SeasonalPattern(topic="tax", start_month=1, peak_month=4, decline_month=5, historical_years_observed=3, confidence=0.92),
        "black_friday": SeasonalPattern(topic="black_friday", start_month=10, peak_month=11, decline_month=12, historical_years_observed=4, confidence=0.95),
        "back_to_school": SeasonalPattern(topic="back_to_school", start_month=7, peak_month=8, decline_month=9, historical_years_observed=3, confidence=0.88),
    }

    @classmethod
    def get_seasonal_pattern(cls, topic: str) -> SeasonalPattern | None:
        norm = topic.lower().replace(" ", "_")
        for key, pat in cls.KNOWN_PATTERNS.items():
            if key in norm or norm in key:
                return pat
        return None

    @classmethod
    def classify_trend_lifecycle(
        cls,
        days_active: int,
        daily_impressions: list[int],
    ) -> TrendLifecycleClass:
        """
        Categorizes how a search trend is evolving over time (Section 112, 113).
        """
        if days_active <= 3 and max(daily_impressions or [0]) > 1000:
            return TrendLifecycleClass.FLASH

        if days_active <= 21:
            return TrendLifecycleClass.SHORT_LIVED

        if len(daily_impressions) >= 30:
            recent_avg = sum(daily_impressions[-7:]) / 7
            historical_avg = sum(daily_impressions) / len(daily_impressions)
            if recent_avg >= (historical_avg * 0.8):
                return TrendLifecycleClass.EVERGREEN_TRANSITION

        return TrendLifecycleClass.SUSTAINED
