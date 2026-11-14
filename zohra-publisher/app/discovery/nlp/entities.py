"""
Zohra — Entity Extraction & Canonical Normalization.

Extracts structured entities from text:
- ORGANIZATION, PERSON, PRODUCT, TECHNOLOGY, LOCATION, MONEY, DATE
Normalizes variants to single canonical names without ambiguous over-merging:
- "OpenAI", "Open AI", "OpenAI Inc." -> "OpenAI"
- "Google LLC", "Google Inc." -> "Google"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.constants import EntityType


@dataclass
class ExtractedEntity:
    entity_type: EntityType
    canonical_name: str
    normalized_name: str
    confidence: float
    mentions: int = 1
    aliases: list[str] = field(default_factory=list)


# Known canonical organizations & aliases
CANONICAL_ORGS: dict[str, tuple[str, list[str]]] = {
    "openai": ("OpenAI", ["Open AI", "OpenAI Inc.", "OpenAI LLC", "OpenAI, Inc."]),
    "google": ("Google", ["Google LLC", "Google Inc.", "Alphabet", "Alphabet Inc."]),
    "microsoft": ("Microsoft", ["Microsoft Corp", "Microsoft Corporation"]),
    "apple": ("Apple", ["Apple Inc.", "Apple Computer"]),
    "meta": ("Meta", ["Meta Platforms", "Meta Inc.", "Facebook"]),
    "nvidia": ("NVIDIA", ["Nvidia", "NVIDIA Corp", "NVIDIA Corporation"]),
    "anthropic": ("Anthropic", ["Anthropic PBC", "Anthropic AI"]),
    "amazon": ("Amazon", ["Amazon.com", "AWS", "Amazon Web Services"]),
    "tesla": ("Tesla", ["Tesla Inc.", "Tesla Motors"]),
    "sec": ("SEC", ["Securities and Exchange Commission"]),
    "fda": ("FDA", ["Food and Drug Administration"]),
    "ftc": ("FTC", ["Federal Trade Commission"]),
    "eu_commission": ("European Commission", ["EU Commission"]),
}

# Known canonical people
CANONICAL_PEOPLE: dict[str, tuple[str, list[str]]] = {
    "sam_altman": ("Sam Altman", ["Altman", "Samuel H. Altman"]),
    "satya_nadella": ("Satya Nadella", ["Nadella"]),
    "sundar_pichai": ("Sundar Pichai", ["Pichai"]),
    "elon_musk": ("Elon Musk", ["Musk"]),
    "jensen_huang": ("Jensen Huang", ["Huang"]),
    "tim_cook": ("Tim Cook", ["Cook"]),
    "mark_zuckerberg": ("Mark Zuckerberg", ["Zuckerberg"]),
    "dario_amodei": ("Dario Amodei", ["Amodei"]),
    "demis_hassabis": ("Demis Hassabis", ["Hassabis"]),
}

# Known canonical products
CANONICAL_PRODUCTS: dict[str, tuple[str, list[str]]] = {
    "gpt_4": ("GPT-4", ["GPT 4", "GPT4", "GPT-4o"]),
    "gpt_5": ("GPT-5", ["GPT 5", "GPT5"]),
    "claude_3": ("Claude 3", ["Claude 3.5", "Claude 3 Opus", "Claude 3 Sonnet"]),
    "gemini": ("Gemini", ["Google Gemini", "Gemini 1.5", "Gemini 1.5 Pro", "Gemini Ultra"]),
    "llama_3": ("Llama 3", ["Llama 3.1", "Llama3", "Meta Llama 3"]),
    "iphone_16": ("iPhone 16", ["iPhone 16 Pro", "Apple iPhone 16"]),
    "windows_11": ("Windows 11", ["Win 11", "Windows11"]),
    "cybercab": ("CyberCab", ["Cybercab", "Robotaxi", "Cyber Cab", "Tesla Cybercab"]),
}

# Known canonical technologies
CANONICAL_TECH: dict[str, tuple[str, list[str]]] = {
    "artificial_intelligence": ("Artificial Intelligence", ["AI", "A.I."]),
    "large_language_model": ("Large Language Models", ["LLM", "LLMs"]),
    "generative_ai": ("Generative AI", ["GenAI"]),
    "autonomous_agents": ("Autonomous Agents", ["AI Agents", "Agentic AI"]),
    "quantum_computing": ("Quantum Computing", ["Quantum Computer"]),
    "semiconductors": ("Semiconductors", ["Chips", "Silicon", "Microchips"]),
    "robotics": ("Robotics", ["Humanoid Robots"]),
}


def normalize_entity_key(name: str) -> str:
    """Produces clean lower_snake_case key for lookup."""
    clean = re.sub(r"[^\w\s]", "", name.lower())
    return re.sub(r"\s+", "_", clean).strip("_")


def extract_entities(text: str) -> list[ExtractedEntity]:
    """
    Extracts structured entities across PERSON, ORGANIZATION, PRODUCT,
    TECHNOLOGY, LOCATION, MONEY, and DATE categories.
    """
    if not text:
        return []

    entities: dict[tuple[EntityType, str], ExtractedEntity] = {}

    def _add_entity(
        etype: EntityType,
        canonical: str,
        norm_key: str,
        confidence: float,
        aliases: list[str] | None = None,
    ) -> None:
        key = (etype, norm_key)
        if key in entities:
            entities[key].mentions += 1
            entities[key].confidence = min(0.99, entities[key].confidence + 0.05)
        else:
            entities[key] = ExtractedEntity(
                entity_type=etype,
                canonical_name=canonical,
                normalized_name=norm_key,
                confidence=confidence,
                mentions=1,
                aliases=aliases or [],
            )

    # 1. Match Known Organizations
    for norm_key, (canonical, aliases) in CANONICAL_ORGS.items():
        all_terms = [canonical] + aliases
        for term in all_terms:
            pattern = rf"\b{re.escape(term)}\b"
            matches = len(re.findall(pattern, text, flags=re.IGNORECASE))
            if matches > 0:
                for _ in range(matches):
                    _add_entity(EntityType.ORGANIZATION, canonical, norm_key, 0.95, aliases)
                break

    # 2. Match Known People
    for norm_key, (canonical, aliases) in CANONICAL_PEOPLE.items():
        all_terms = [canonical] + aliases
        for term in all_terms:
            pattern = rf"\b{re.escape(term)}\b"
            matches = len(re.findall(pattern, text, flags=re.IGNORECASE))
            if matches > 0:
                for _ in range(matches):
                    _add_entity(EntityType.PERSON, canonical, norm_key, 0.95, aliases)
                break

    # 3. Match Known Products
    for norm_key, (canonical, aliases) in CANONICAL_PRODUCTS.items():
        all_terms = [canonical] + aliases
        for term in all_terms:
            pattern = rf"\b{re.escape(term)}\b"
            matches = len(re.findall(pattern, text, flags=re.IGNORECASE))
            if matches > 0:
                for _ in range(matches):
                    _add_entity(EntityType.PRODUCT, canonical, norm_key, 0.95, aliases)
                break

    # 4. Match Known Technologies
    for norm_key, (canonical, aliases) in CANONICAL_TECH.items():
        all_terms = [canonical] + aliases
        for term in all_terms:
            pattern = rf"\b{re.escape(term)}\b"
            matches = len(re.findall(pattern, text, flags=re.IGNORECASE))
            if matches > 0:
                for _ in range(matches):
                    _add_entity(EntityType.TECHNOLOGY, canonical, norm_key, 0.90, aliases)
                break

    # 5. Extract Money values (e.g. $5 billion, €100M, $500,000)
    money_matches = re.finditer(
        r"(\$|€|£|₹)\s?(\d+(?:,\d+)*(?:\.\d+)?)\s*(billion|million|trillion|crore|lakh|k|b|m)?\b",
        text,
        flags=re.IGNORECASE,
    )
    for m in money_matches:
        raw_val = m.group(0).strip()
        norm_val = normalize_entity_key(raw_val)
        _add_entity(EntityType.MONEY, raw_val, f"money_{norm_val}", 0.85)

    # 6. Extract Dynamic Capitalized Names (e.g. "CEO Tim Cook", "Dr. Jane Doe")
    person_dynamic = re.finditer(
        r"\b(?:Mr\.|Ms\.|Mrs\.|Dr\.|CEO|CTO|President|Founder|Director)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+))\b",
        text,
    )
    for m in person_dynamic:
        full_name = m.group(1).strip()
        norm_key = normalize_entity_key(full_name)
        _add_entity(EntityType.PERSON, full_name, norm_key, 0.80)

    return list(entities.values())


class EntityExtractor:
    @staticmethod
    def extract_entities(text: str) -> list[dict]:
        extracted = extract_entities(text)
        return [
            {
                "entity_type": e.entity_type,
                "canonical_name": e.canonical_name,
                "normalized_name": e.normalized_name,
                "confidence": e.confidence,
                "mentions": e.mentions,
                "aliases": e.aliases,
            }
            for e in extracted
        ]

    @staticmethod
    def normalize_canonical(name: str) -> str:
        k = normalize_entity_key(name)
        if k in CANONICAL_ORGS:
            return CANONICAL_ORGS[k][0]
        # Check aliases
        for canonical, aliases in CANONICAL_ORGS.values():
            if name.lower() == canonical.lower() or any(name.lower() == a.lower() for a in aliases):
                return canonical
        for canonical, aliases in CANONICAL_PEOPLE.values():
            if name.lower() == canonical.lower() or any(name.lower() == a.lower() for a in aliases):
                return canonical
        for canonical, aliases in CANONICAL_PRODUCTS.values():
            if name.lower() == canonical.lower() or any(name.lower() == a.lower() for a in aliases):
                return canonical
        for canonical, aliases in CANONICAL_TECH.values():
            if name.lower() == canonical.lower() or any(name.lower() == a.lower() for a in aliases):
                return canonical
        clean = (
            re.sub(r"\b(Inc\.?|LLC|Corp\.?|Corporation|Ltd\.?)\b", "", name, flags=re.IGNORECASE)
            .strip()
            .rstrip(".,")
        )
        return clean or name
