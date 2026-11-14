"""
Zohra — Semantic SEO Optimizer (Part 5).

Optimizes articles for search engines and human readers:
heading hierarchy (single H1, clean H2/H3s), natural keyword distribution,
slug candidates, meta titles/descriptions, structured schema candidates,
and calculates comprehensive SEO content scores.
"""

from __future__ import annotations

import re


class SemanticSEOOptimizer:
    """Manages semantic search optimization without manipulative stuffing."""

    STOPWORDS = {
        "a", "an", "the", "in", "on", "at", "to", "for", "with", "and", "or",
        "of", "by", "from", "is", "are", "was", "were", "it", "this", "that",
    }

    @classmethod
    def generate_slug(cls, title: str, primary_keyword: str) -> str:
        """Generates a clean, readable, descriptive URL slug."""
        text = primary_keyword.strip() if len(primary_keyword.split()) >= 2 else title
        text = text.lower()
        # Remove special characters
        text = re.sub(r"[^\w\s-]", "", text)
        words = text.split()
        # Remove non-essential stopwords if slug is too long
        if len(words) > 5:
            words = [w for w in words if w not in cls.STOPWORDS]
        slug = "-".join(words[:6])
        return re.sub(r"-+", "-", slug).strip("-")

    @classmethod
    def generate_meta_title(cls, headline: str, primary_keyword: str) -> str:
        """Generates a natural meta title (target 50-65 chars)."""
        if len(headline) <= 65 and primary_keyword.lower() in headline.lower():
            return headline
        # Construct compact version
        clean_kw = primary_keyword.title()
        if clean_kw in headline:
            return headline[:65].rsplit(" ", 1)[0]
        return f"{clean_kw}: Complete Guide & Breakdown"[:65]

    @classmethod
    def generate_meta_description(cls, topic: str, primary_keyword: str, promise: str) -> str:
        """Generates an accurate, value-focused meta description (target 140-160 chars)."""
        desc = f"Explore our evidence-backed guide to {primary_keyword}. {promise}"
        if len(desc) > 160:
            desc = desc[:157].rsplit(" ", 1)[0] + "..."
        elif len(desc) < 130:
            desc = f"Comprehensive, verified guide to {primary_keyword}. {promise} Read the full breakdown of features, pricing, and limitations."
            if len(desc) > 160:
                desc = desc[:157].rsplit(" ", 1)[0] + "..."
        return desc

    @classmethod
    def evaluate_heading_hierarchy(cls, content: str) -> tuple[float, list[str]]:
        """Validates heading hierarchy (single H1, logical H2/H3 progression).

        Returns (hierarchy_score, issues).
        """
        issues = []
        h1_matches = re.findall(r"^#\s+(.+)$", content, re.MULTILINE)
        h2_matches = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)

        if len(h1_matches) == 0:
            issues.append("Missing H1 title heading.")
        elif len(h1_matches) > 1:
            issues.append(f"Multiple H1 headings found ({len(h1_matches)}); expected exactly one.")

        if len(h2_matches) < 2:
            issues.append(f"Insufficient major sections ({len(h2_matches)} H2 headings); expected at least 2.")

        score = 100.0 - (len(issues) * 20.0)
        return max(20.0, score), issues

    @classmethod
    def calculate_seo_content_score(
        cls,
        title: str,
        content: str,
        primary_keyword: str,
        secondary_keywords: list[str] | None = None,
        has_faq: bool = False,
        has_table: bool = False,
    ) -> float:
        """Calculates 0-100 SEO content score based on structure, keyword naturalness, and snippet readiness."""
        pk_lower = primary_keyword.lower()
        c_lower = content.lower()
        t_lower = title.lower()

        score = 60.0

        # 1. Title keyword presence
        if pk_lower in t_lower:
            score += 10.0

        # 2. Body keyword presence & density check (prevent stuffing)
        kw_count = len(re.findall(r"\b" + re.escape(pk_lower) + r"\b", c_lower))
        total_words = max(1, len(content.split()))
        density = (kw_count * len(pk_lower.split())) / total_words

        if 0.005 <= density <= 0.05:
            # Ideal natural density (0.5% - 5.0%)
            score += 10.0
        elif density > 0.08 and kw_count > 4:
            # Aggressive stuffing penalty
            score -= 25.0
        elif kw_count > 0:
            score += 5.0

        # 3. Secondary keyword inclusion
        if secondary_keywords:
            included = sum(1 for sk in secondary_keywords if sk.lower() in c_lower)
            sec_ratio = included / len(secondary_keywords)
            score += (sec_ratio * 10.0)

        # 4. Heading structure score
        h_score, _ = cls.evaluate_heading_hierarchy(content)
        score += (h_score * 0.05)

        # 5. Featured snippet readiness (FAQ / Table structures)
        if has_table:
            score += 2.5
        if has_faq:
            score += 2.5

        return round(max(0.0, min(100.0, score)), 1)
