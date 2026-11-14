"""
Zohra — Source Diversity Score Calculator.

Ensures that 20 articles copied from one press release or syndicate
do not count like 20 independent discoveries:
- Evaluates distinct domains
- Evaluates tier distribution (Tier 1 official, Tier 2 press, etc.)
- Evaluates geographical diversity
"""

from __future__ import annotations


def calculate_source_diversity_score(
    domains: list[str],
    tiers: list[int],
    countries: list[str],
) -> float:
    """
    Computes Source Diversity Score [0.0 - 100.0].
    """
    if not domains:
        return 0.0

    unique_domains = len(set(domains))
    unique_tiers = set(tiers)
    unique_countries = len(set(c for c in countries if c))

    # 1. Unique domains contribution (up to 50 points)
    # 1 domain = 15pts, 3 domains = 35pts, 5+ domains = 50pts
    domain_score = min(50.0, unique_domains * 10.0)

    # 2. Tier diversity (up to 30 points)
    # Having Tier 1 (official) + Tier 2 (press) indicates high cross-validation
    tier_score = 0.0
    if 1 in unique_tiers:
        tier_score += 15.0  # Official source present
    if 2 in unique_tiers:
        tier_score += 10.0  # Established press present
    if 3 in unique_tiers or 4 in unique_tiers:
        tier_score += 5.0  # Specialist or community present

    # 3. Country / regional diversity (up to 20 points)
    country_score = min(20.0, unique_countries * 10.0)

    total = domain_score + tier_score + country_score
    return min(100.0, max(0.0, round(total, 2)))


def calculate_source_diversity(sources: list) -> float:
    """Wrapper accepting list of source objects/mocks."""
    domains = [getattr(s, "domain", "") for s in sources]
    tiers = [
        s.tier.value if hasattr(getattr(s, "tier", None), "value") else int(getattr(s, "tier", 3))
        for s in sources
    ]
    countries = [getattr(s, "country", "") for s in sources]
    return calculate_source_diversity_score(domains, tiers, countries)
