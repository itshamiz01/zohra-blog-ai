"""
Zohra — Topic Classification & Taxonomy.

Assigns documents and events to configurable categories:
- Multi-label classification with confidence scores
- Configurable taxonomy (enabled/disabled/review-only)
- Deterministic keyword and semantic signal matching
"""

from __future__ import annotations

import re

# Category configuration / status
CATEGORY_POLICY: dict[str, str] = {
    "Artificial Intelligence": "ENABLED",
    "Technology": "ENABLED",
    "Business": "ENABLED",
    "Science": "ENABLED",
    "Entertainment": "ENABLED",
    "Gaming": "ENABLED",
    "Automotive": "ENABLED",
    "Finance": "REVIEW_ONLY",
    "Health": "REVIEW_ONLY",
    "Politics": "DISABLED",
}

# Category signal keyword dictionaries
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Artificial Intelligence": [
        "artificial intelligence",
        "ai",
        "llm",
        "large language model",
        "machine learning",
        "deep learning",
        "neural network",
        "chatgpt",
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "autonomous agent",
        "generative ai",
        "diffusion model",
        "transformer",
    ],
    "Technology": [
        "technology",
        "tech",
        "software",
        "hardware",
        "apple",
        "google",
        "microsoft",
        "smartphone",
        "computer",
        "cloud",
        "server",
        "chip",
        "semiconductor",
        "nvidia",
        "cybersecurity",
        "app",
        "operating system",
        "developer",
        "api",
        "database",
    ],
    "Business": [
        "business",
        "company",
        "startup",
        "revenue",
        "profit",
        "quarter",
        "earnings",
        "acquisition",
        "merger",
        "ceo",
        "shares",
        "stock",
        "funding",
        "round",
        "investor",
        "valuation",
        "ipo",
        "market cap",
    ],
    "Science": [
        "science",
        "research",
        "study",
        "space",
        "nasa",
        "physics",
        "biology",
        "astronomy",
        "telescope",
        "climate",
        "discovery",
        "laboratory",
        "scientist",
        "dna",
        "crispr",
    ],
    "Entertainment": [
        "movie",
        "film",
        "actor",
        "actress",
        "cinema",
        "music",
        "album",
        "song",
        "streaming",
        "netflix",
        "disney",
        "hollywood",
        "box office",
        "trailer",
        "series",
        "concert",
    ],
    "Gaming": [
        "game",
        "gaming",
        "playstation",
        "xbox",
        "nintendo",
        "steam",
        "esports",
        "pc gaming",
        "rpg",
        "multiplayer",
        "gameplay",
        "console",
        "epic games",
        "valve",
    ],
    "Automotive": [
        "car",
        "vehicle",
        "electric vehicle",
        "ev",
        "tesla",
        "automotive",
        "auto",
        "engine",
        "battery",
        "autonomous driving",
        "driverless",
        "toyota",
        "ford",
        "bmw",
    ],
    "Finance": [
        "finance",
        "bank",
        "crypto",
        "bitcoin",
        "ethereum",
        "blockchain",
        "interest rate",
        "inflation",
        "federal reserve",
        "central bank",
        "wall street",
        "bond",
    ],
    "Health": [
        "health",
        "medical",
        "disease",
        "vaccine",
        "hospital",
        "patient",
        "treatment",
        "fda",
        "drug",
        "clinical trial",
        "cancer",
        "therapy",
        "physician",
        "doctor",
    ],
    "Politics": [
        "election",
        "president",
        "prime minister",
        "senate",
        "congress",
        "parliament",
        "vote",
        "ballot",
        "campaign",
        "democrat",
        "republican",
        "legislation",
        "treaty",
    ],
}


def classify_topics(text: str) -> tuple[str, dict[str, float]]:
    """
    Classifies text into categories.
    Returns (primary_category, dict_of_all_matched_categories_with_scores).
    """
    if not text:
        return "Technology", {"Technology": 0.50}

    text_lower = text.lower()
    scores: dict[str, float] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        # Skip disabled categories from active scoring
        if CATEGORY_POLICY.get(category) == "DISABLED":
            continue

        match_count = 0
        for kw in keywords:
            # Word boundary regex for short terms like 'ai' or 'ev', substring for phrases
            if len(kw) <= 3:
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, text_lower):
                    match_count += 1
            else:
                if kw in text_lower:
                    match_count += 1

        if match_count > 0:
            # Confidence score between 0.50 and 0.99
            confidence = min(0.99, 0.40 + (match_count * 0.12))
            scores[category] = round(confidence, 2)

    if not scores:
        return "Technology", {"Technology": 0.50}

    # Determine primary category (highest score)
    primary = max(scores.items(), key=lambda x: x[1])[0]
    return primary, scores


class TopicClassifier:
    @staticmethod
    def classify(text: str) -> dict[str, float]:
        _, scores = classify_topics(text)
        return scores
