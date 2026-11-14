"""
Zohra — Risk Flags & High-Verification Detector.

Scans content for sensitive, legal, financial, health, or defamatory claims:
- Identifies risk flags (medical, financial, legal, death, allegation, crime, etc.)
- Enforces HIGH_VERIFICATION_REQUIRED when serious claims concern identifiable persons.
"""

from __future__ import annotations

import re

from app.core.constants import RiskFlag

# Pattern dictionaries for each risk category
RISK_PATTERNS: dict[RiskFlag, re.Pattern] = {
    RiskFlag.MEDICAL: re.compile(
        r"\b(cancer|vaccine|fda\s+warning|cure|mortality|clinical\s+trial|pandemic|side\s+effect)\b",
        re.IGNORECASE,
    ),
    RiskFlag.FINANCIAL: re.compile(
        r"\b(buy\s+now|investment\s+advice|crypto\s+token|guaranteed\s+return|ponzi|insider\s+trading|securities\s+fraud)\b",
        re.IGNORECASE,
    ),
    RiskFlag.LEGAL: re.compile(
        r"\b(lawsuit|subpoena|indictment|sued|injunction|settlement|plaintiff|defendant|court\s+ruling)\b",
        re.IGNORECASE,
    ),
    RiskFlag.POLITICAL: re.compile(
        r"\b(election\s+fraud|impeachment|foreign\s+interference|propaganda|conspiracy)\b",
        re.IGNORECASE,
    ),
    RiskFlag.VIOLENCE: re.compile(
        r"\b(shooting|terrorist|explosion|hostage|massacre|assassination|bombing)\b",
        re.IGNORECASE,
    ),
    RiskFlag.DEATH: re.compile(
        r"\b(died|dead|death|passed\s+away|killed|fatal|deceased|found\s+dead|cause\s+of\s+death)\b",
        re.IGNORECASE,
    ),
    RiskFlag.ALLEGATION: re.compile(
        r"\b(alleged|accused|claims\s+of|allegations|misconduct|harassment|defrauded|embezzled)\b",
        re.IGNORECASE,
    ),
    RiskFlag.CRIME: re.compile(
        r"\b(arrested|charged\s+with|convicted|guilty|felony|fbi|doj|money\s+laundering|bribery)\b",
        re.IGNORECASE,
    ),
    RiskFlag.MINOR: re.compile(
        r"\b(minor|child|children|juvenile|underage)\b",
        re.IGNORECASE,
    ),
    RiskFlag.PRIVACY: re.compile(
        r"\b(data\s+breach|hacked|leaked\s+passwords|stolen\s+credentials|ransomware|doxxed)\b",
        re.IGNORECASE,
    ),
    RiskFlag.BREAKING_EMERGENCY: re.compile(
        r"\b(breaking\s+news|active\s+shooter|evacuation|state\s+of\s+emergency|air\s+raid)\b",
        re.IGNORECASE,
    ),
}

# Serious personal claims that trigger high verification requirement
PERSON_CRITICAL_FLAGS = {
    RiskFlag.DEATH,
    RiskFlag.ALLEGATION,
    RiskFlag.CRIME,
    RiskFlag.LEGAL,
}


def detect_risk_flags(
    text: str,
    has_person_entity: bool = False,
) -> tuple[list[str], bool]:
    """
    Detects risk flags in text.
    Returns (list_of_risk_flag_strings, high_verification_required_bool).
    """
    if not text:
        return [], False

    detected_flags: list[RiskFlag] = []

    for flag, pattern in RISK_PATTERNS.items():
        if pattern.search(text):
            detected_flags.append(flag)

    high_verification_required = False

    # Section 73: If an event contains serious claims about an identifiable person,
    # automatically mark HIGH_VERIFICATION_REQUIRED
    if has_person_entity:
        for f in detected_flags:
            if f in PERSON_CRITICAL_FLAGS:
                high_verification_required = True
                break

    # Also require high verification if breaking emergency or violence
    if RiskFlag.BREAKING_EMERGENCY in detected_flags or RiskFlag.VIOLENCE in detected_flags:
        high_verification_required = True

    return [f.value for f in detected_flags], high_verification_required


class RiskDetector:
    @staticmethod
    def detect_risks(text: str) -> tuple[list[RiskFlag], bool]:
        flags_str, high_verif = detect_risk_flags(text, has_person_entity=True)
        return [RiskFlag(f) for f in flags_str], high_verif
