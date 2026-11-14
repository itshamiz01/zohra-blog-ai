"""
Zohra — Claim Canonicalizer & Numeric/Date Normalizer.

Transforms raw claim texts into structured (subject, predicate, object, qualifiers, scope)
representations, normalizes numbers, currencies, and dates while strictly preserving scope.
"""

from __future__ import annotations

import contextlib
import re
from datetime import datetime
from typing import Any


class CanonicalClaimData:
    def __init__(
        self,
        subject: str | None,
        predicate: str | None,
        object_value: str | None,
        numeric_value: float | None = None,
        unit: str | None = None,
        currency: str | None = None,
        region: str | None = None,
        temporal_scope: str | None = None,
        effective_date: datetime | None = None,
    ):
        self.subject = subject
        self.predicate = predicate
        self.object_value = object_value
        self.numeric_value = numeric_value
        self.unit = unit
        self.currency = currency
        self.region = region
        self.temporal_scope = temporal_scope
        self.effective_date = effective_date

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object_value": self.object_value,
            "numeric_value": self.numeric_value,
            "unit": self.unit,
            "currency": self.currency,
            "region": self.region,
            "temporal_scope": self.temporal_scope,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
        }

    def canonical_signature(self) -> str:
        """Returns deterministic hash signature for deduplication preserving scope."""
        s = (self.subject or "").lower().strip()
        p = (self.predicate or "").lower().strip()
        o = (self.object_value or "").lower().strip()
        r = (self.region or "global").lower().strip()
        t = (self.temporal_scope or "any").lower().strip()
        return f"{s}|{p}|{o}|{r}|{t}"


class ClaimCanonicalizer:
    """Extracts structured values, currencies, units, dates, and regions from claims."""

    CURRENCY_REGEX = re.compile(
        r"(?:(\$|₹|€|£|USD|INR|EUR|GBP)\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(USD|INR|EUR|GBP|dollars|rupees))",
        re.I,
    )
    CURRENCY_MAP = {
        "$": "USD",
        "usd": "USD",
        "dollars": "USD",
        "₹": "INR",
        "inr": "INR",
        "rupees": "INR",
        "€": "EUR",
        "eur": "EUR",
        "£": "GBP",
        "gbp": "GBP",
    }

    NUMERIC_UNIT_REGEX = re.compile(
        r"\b([\d,]+(?:\.\d+)?)\s*(GB|MB|TB|hours|mins|minutes|seconds|fps|k|users|tokens|generations|%|percent)\b",
        re.I,
    )

    REGION_PATTERNS = [
        ("India", re.compile(r"\b(?:India|INR|₹|Indian)\b", re.I)),
        ("US", re.compile(r"\b(?:United States|USA|U\.S\.|US|USD)\b", re.I)),
        ("UK", re.compile(r"\b(?:United Kingdom|UK|Britain|GBP|£)\b", re.I)),
        ("EU", re.compile(r"\b(?:Europe|European Union|EU|EUR|€)\b", re.I)),
    ]

    DATE_YEAR_REGEX = re.compile(r"\b(202[0-9])\b")
    DATE_MONTH_YEAR_REGEX = re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(202[0-9])\b",
        re.I,
    )
    DATE_EXACT_REGEX = re.compile(
        r"\b(202[0-9][-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12][0-9]|3[01]))\b"
    )

    @classmethod
    def canonicalize(cls, claim_text: str, context_region: str | None = None) -> CanonicalClaimData:
        text = claim_text.strip()
        numeric_val: float | None = None
        unit: str | None = None
        currency: str | None = None
        region: str | None = context_region
        temporal_scope: str | None = None
        effective_date: datetime | None = None

        # 1. Parse currency and price values
        curr_match = cls.CURRENCY_REGEX.search(text)
        if curr_match:
            c1, v1, v2, c2 = curr_match.groups()
            raw_c = c1 or c2 or ""
            raw_v = v1 or v2 or ""
            currency = cls.CURRENCY_MAP.get(raw_c.lower().strip(), raw_c.upper().strip())
            with contextlib.suppress(ValueError):
                numeric_val = float(raw_v.replace(",", ""))

        # 2. Parse general numeric units
        if numeric_val is None:
            num_match = cls.NUMERIC_UNIT_REGEX.search(text)
            if num_match:
                raw_num, raw_unit = num_match.groups()
                with contextlib.suppress(ValueError):
                    numeric_val = float(raw_num.replace(",", ""))
                    unit = raw_unit.upper().strip()

        # 3. Detect Region
        for reg_name, reg_pat in cls.REGION_PATTERNS:
            if reg_pat.search(text):
                region = reg_name
                break

        # 4. Detect Dates
        exact_match = cls.DATE_EXACT_REGEX.search(text)
        if exact_match:
            try:
                ds = exact_match.group(1).replace("/", "-").replace(".", "-")
                effective_date = datetime.fromisoformat(ds)
                temporal_scope = ds
            except (ValueError, TypeError):
                pass
        else:
            month_match = cls.DATE_MONTH_YEAR_REGEX.search(text)
            if month_match:
                temporal_scope = f"{month_match.group(1)} {month_match.group(2)}"
            else:
                year_match = cls.DATE_YEAR_REGEX.search(text)
                if year_match:
                    temporal_scope = year_match.group(1)

        # 5. Extract Subject / Predicate / Object heuristic
        words = text.split()
        subject = " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else None)
        predicate = None
        object_value = None

        if any(w in text.lower() for w in ("cost", "price", "pricing", "$", "₹")):
            predicate = "pricing"
            object_value = f"{numeric_val} {currency}" if (numeric_val and currency) else text
        elif any(w in text.lower() for w in ("launch", "released", "announced")):
            predicate = "release_event"
            object_value = temporal_scope or text
        elif any(w in text.lower() for w in ("support", "feature", "generate", "include")):
            predicate = "capability"
            object_value = text
        elif any(w in text.lower() for w in ("limit", "problem", "error", "restriction", "lack")):
            predicate = "limitation"
            object_value = text
        else:
            predicate = "statement"
            object_value = text

        return CanonicalClaimData(
            subject=subject,
            predicate=predicate,
            object_value=object_value,
            numeric_value=numeric_val,
            unit=unit,
            currency=currency,
            region=region,
            temporal_scope=temporal_scope,
            effective_date=effective_date,
        )
