"""
Zohra — Geography & Country Detection.

Derives country and geographic scope from:
- Explicit country mentions in document text/title
- Source domain TLD (.in, .uk, .de, .jp, .ca, .au, .fr)
- Explicit source country configuration
Avoids speculative guessing without evidence.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Country TLD mapping
TLD_COUNTRY_MAP: dict[str, str] = {
    "in": "IN",
    "uk": "GB",
    "co.uk": "GB",
    "de": "DE",
    "fr": "FR",
    "jp": "JP",
    "co.jp": "JP",
    "ca": "CA",
    "au": "AU",
    "com.au": "AU",
    "br": "BR",
    "com.br": "BR",
    "ru": "RU",
    "cn": "CN",
    "sg": "SG",
    "ae": "AE",
    "sa": "SA",
}

# Country name patterns
COUNTRY_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "US",
        re.compile(
            r"\b(United States|U\.S\.|USA|Washington D\.C\.|Silicon Valley)\b", re.IGNORECASE
        ),
    ),
    (
        "IN",
        re.compile(r"\b(India|New Delhi|Bengaluru|Bangalore|Mumbai|Hyderabad)\b", re.IGNORECASE),
    ),
    ("GB", re.compile(r"\b(United Kingdom|U\.K\.|Britain|London|Downing Street)\b", re.IGNORECASE)),
    ("EU", re.compile(r"\b(European Union|EU Commission|Brussels|Europe)\b", re.IGNORECASE)),
    ("DE", re.compile(r"\b(Germany|Berlin|Munich|Frankfurt)\b", re.IGNORECASE)),
    ("FR", re.compile(r"\b(France|Paris)\b", re.IGNORECASE)),
    ("JP", re.compile(r"\b(Japan|Tokyo)\b", re.IGNORECASE)),
    ("CN", re.compile(r"\b(China|Beijing|Shanghai|Shenzhen)\b", re.IGNORECASE)),
    ("CA", re.compile(r"\b(Canada|Ottawa|Toronto|Vancouver)\b", re.IGNORECASE)),
    ("AU", re.compile(r"\b(Australia|Canberra|Sydney|Melbourne)\b", re.IGNORECASE)),
]


def detect_country(
    text: str,
    url: str | None = None,
    source_country: str | None = None,
) -> str | None:
    """
    Detect country context based on source configuration, domain TLD,
    and explicit text entities. Returns 2-letter ISO code or None if global/unclear.
    """
    # 1. Source country config takes precedence if provided and not "global"
    if source_country and len(source_country.strip()) == 2 and source_country.upper() != "GL":
        return source_country.strip().upper()

    # 2. Check domain TLD
    if url:
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            parts = host.split(".")
            if len(parts) >= 2:
                # Check 2-part TLD (e.g. co.uk)
                two_tld = ".".join(parts[-2:])
                if two_tld in TLD_COUNTRY_MAP:
                    return TLD_COUNTRY_MAP[two_tld]
                # Check 1-part TLD (e.g. in, de)
                one_tld = parts[-1]
                if one_tld in TLD_COUNTRY_MAP:
                    return TLD_COUNTRY_MAP[one_tld]
        except (ValueError, AttributeError):
            pass

    # 3. Check explicit text entities in title and first 1000 chars
    sample = text[:1500] if text else ""
    for country_code, pattern in COUNTRY_PATTERNS:
        if pattern.search(sample):
            return country_code

    return None


class GeographyDetector:
    @staticmethod
    def detect_country(domain: str | None = None, text: str = "") -> str:
        c = detect_country(text=text, url=f"https://{domain}" if domain else None)
        return c or "global"
