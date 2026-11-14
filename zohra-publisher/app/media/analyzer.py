"""
Zohra — Article Visual Analyzer.

Extracts deep contextual and visualizable concepts from approved articles,
filtering out generic tropes and defending against prompt injection.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger
from app.llm.base import LLMRole
from app.llm.registry import get_default_provider
from app.media.models import VisualAnalysis

logger = get_logger("media.analyzer")

# Dangerous prompt injection phrases in untrusted article body
INJECTION_PATTERN = re.compile(
    r"(ignore\s+(all\s+)?(previous\s+)?instructions|system\s+prompt|reveal\s+api\s+key|bypass\s+safety|delete\s+database)",
    re.IGNORECASE,
)


class ArticleVisualAnalyzer:
    """Understands the core meaning and visual themes of an approved article."""

    @classmethod
    def sanitize_untrusted_text(cls, text: str) -> str:
        """Removes or neutralizes malicious prompt injection attempts from article text."""
        if not text:
            return ""
        # Strip dangerous directives
        sanitized = INJECTION_PATTERN.sub("[redacted instruction]", text)
        return sanitized.strip()

    @classmethod
    async def analyze(
        cls,
        title: str,
        topic: str,
        category: str = "Technology",
        audience: str = "Learners and Practitioners",
        tone: str = "Authoritative and Practical",
        sections: list[dict[str, Any]] | None = None,
        full_text: str = "",
        brand_identity: str = "Modern High-Authority Editorial",
    ) -> VisualAnalysis:
        """
        Analyzes the article to produce structured visualizable entities and guardrails.
        """
        safe_title = cls.sanitize_untrusted_text(title)
        safe_topic = cls.sanitize_untrusted_text(topic or "Technology & Learning")
        safe_body = cls.sanitize_untrusted_text(full_text[:4000])

        # Heuristic extraction of visualizable themes and negative guardrails
        visualizable = []
        avoid = [
            "floating generic robots looking at laptops",
            "glowing blue holograms hovering in empty space",
            "fake logos, watermarks, or commercial branding",
            "baked-in headlines, text banners, or typography",
            "distorted anatomy, deformed hands, or extra fingers",
            "misleading depiction of real unverified factual events",
        ]

        title_lower = safe_title.lower()
        if "student" in title_lower or "school" in title_lower or "study" in title_lower:
            visualizable.extend([
                "desk with open notebooks, reference books, and modern tablet/screen",
                "focused student engaged in study and critical thought",
                "clean warm study space with natural desk lighting",
                "subtle visual representation of assistive digital outlines",
            ])
            avoid.append("cartoonish students or exaggerated stressful depictions")
        elif "security" in title_lower or "cyber" in title_lower or "cloud" in title_lower:
            visualizable.extend([
                "sleek modern infrastructure visual",
                "balanced network architecture conceptual visualization",
                "clean server room or architectural workspace",
            ])
            avoid.append("hooded hackers in green binary code matrix")
        elif "reddit" in title_lower or "community" in title_lower or "discussion" in title_lower:
            visualizable.extend([
                "interactive digital forum discussion threads visualized in clean architecture",
                "collaboration hub where questions connect into insights",
            ])
        else:
            visualizable.extend([
                f"central focal subject representing practical implementation of {safe_topic}",
                "modern workspace with authentic human context and tools",
                "balanced composition with depth and natural directional light",
            ])

        # Extract entities from headings
        entities = [safe_topic]
        if sections:
            for s in sections[:5]:
                h = s.get("heading")
                if h:
                    entities.append(cls.sanitize_untrusted_text(h))

        # Attempt LLM enhancement via existing configured OpenAI/OpenRouter router if available
        try:
            provider = get_default_provider(role=LLMRole.CLASSIFICATION)
            if provider and getattr(provider, "name", None) != "mock":
                system_prompt = (
                    "You are an expert editorial art director for a prestigious publication.\n"
                    "Analyze this article to design a sophisticated, authentic visual concept for its featured hero image.\n"
                    "Extract the primary subject, environment, visualizable elements, and what to AVOID.\n"
                    "Do NOT suggest generic AI cliches like floating robots or blue matrix code.\n"
                    "Return a JSON object with keys: primary_subject, important_concepts (list), visualizable_elements (list), things_to_avoid (list)."
                )
                user_msg = (
                    f"<untrusted_article>\n"
                    f"Title: {safe_title}\n"
                    f"Topic: {safe_topic}\n"
                    f"Category: {category}\n"
                    f"Audience: {audience}\n"
                    f"Excerpt: {safe_body[:1000]}\n"
                    f"</untrusted_article>"
                )
                llm_res = await provider.generate_structured_json(
                    prompt=user_msg,
                    system_prompt=system_prompt,
                    schema={
                        "type": "object",
                        "properties": {
                            "primary_subject": {"type": "string"},
                            "important_concepts": {"type": "array", "items": {"type": "string"}},
                            "visualizable_elements": {"type": "array", "items": {"type": "string"}},
                            "things_to_avoid": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["primary_subject", "important_concepts", "visualizable_elements", "things_to_avoid"],
                    },
                )
                if isinstance(llm_res, dict) and llm_res.get("primary_subject"):
                    return VisualAnalysis(
                        article_topic=safe_topic,
                        primary_subject=llm_res["primary_subject"],
                        main_entities=entities[:6],
                        article_category=category,
                        audience=audience,
                        tone=tone,
                        important_concepts=llm_res.get("important_concepts", [safe_topic])[:5],
                        visualizable_elements=llm_res.get("visualizable_elements", visualizable)[:6],
                        things_to_avoid=list(set(avoid + llm_res.get("things_to_avoid", [])))[:8],
                        brand_identity=brand_identity,
                    )
        except Exception as exc:
            logger.debug(f"LLM visual analysis fallback to deterministic heuristics: {exc}")

        # Deterministic fallback
        return VisualAnalysis(
            article_topic=safe_topic,
            primary_subject=f"Practical exploration of {safe_title}",
            main_entities=entities[:5],
            article_category=category,
            audience=audience,
            tone=tone,
            important_concepts=[safe_topic, "Applied Knowledge", "Best Practices"],
            visualizable_elements=visualizable,
            things_to_avoid=avoid,
            brand_identity=brand_identity,
        )
