"""
Zohra — Reddit Response Writer.

Synthesizes high-value, authentic, Reddit-native responses to user questions.
Adheres strictly to the 'Usefulness First' philosophy:
- The answer must be 100% complete and self-contained on Reddit.
- No cliffhangers, no marketing jargon, no deceptive fake-user claims.
- If a link is permitted and adds genuine depth, transparently discloses authorship.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.models.reddit import RedditResponseType
from app.llm.base import LLMRequest, LLMRole
from app.llm.registry import get_default_provider

logger = get_logger("reddit.response_writer")


class GeneratedRedditResponse(BaseModel):
    """Structured response output from response generation engine."""

    response_type: str = Field(default=RedditResponseType.ANSWER_ONLY.value)
    answer_text: str = Field(description="Complete standalone Reddit markdown answer")
    optional_resource_sentence: str | None = Field(
        default=None, description="Transparent resource link sentence if appropriate"
    )
    full_markdown: str = Field(description="Final markdown formatted comment ready for review")
    included_link: str | None = None
    link_rationale: str | None = None


class RedditResponseWriter:
    """Generates authentic, high-quality Reddit community answers."""

    def __init__(self) -> None:
        pass

    async def generate_response(
        self,
        question_title: str,
        question_body: str | None,
        article_title: str | None = None,
        article_url: str | None = None,
        article_excerpt: str | None = None,
        allow_link: bool = False,
    ) -> GeneratedRedditResponse:
        """
        Drafts a comprehensive Reddit-native answer using the active LLM provider.
        """
        supplemental_context = ""
        if article_title:
            supplemental_context = (
                f"SUPPLEMENTAL VERIFIED REFERENCE MATERIAL FROM OUR DETAILED ARTICLE:\n"
                f"Title: \"{article_title}\"\n"
                f"Summary: {article_excerpt or 'Detailed breakdown with primary references'}\n"
            )

        link_instructions = (
            "LINK INCLUSION INSTRUCTION:\n"
            "You may include ONE transparent closing sentence offering our published guide for readers wanting deeper charts or primary sources. Example:\n"
            "\"I put together a deeper breakdown with the full evidence tables here: [link]\""
            if (allow_link and article_url)
            else "LINK POLICY: DO NOT include any links or URLs. Write an ANSWER-ONLY response."
        )

        example_resource = (
            f"I put together a detailed breakdown with the full sources here: [{article_title or 'Guide'}]({article_url})"
            if (allow_link and article_url)
            else ""
        )
        example_rationale = (
            "Provides extended primary source references and data breakdown"
            if allow_link
            else "No link included in accordance with community rules"
        )

        prompt = f"""
You are an expert educator, technologist, and helpful community contributor writing a Reddit comment.

REDDIT POST TO ANSWER:
Title: "{question_title}"
Body:
{question_body or "[No additional body text]"}

{supplemental_context}

EDITORIAL RULES FOR A REDDIT-NATIVE ANSWER:
1. COMPLETE STANDALONE VALUE: Answer the user's dilemma directly and thoroughly in the comment itself. The reader must get full clarity without needing to click any external link.
2. NATURAL TONE: Write in natural, intellectual, respectful Reddit markdown (use bullet points, bold key terms, concise paragraphs).
3. ZERO MARKETING: Absolutely no marketing fluff, corporate jargon, fake enthusiasm, or promotional buzzwords.
4. NO DECEPTION: Never pretend to be a random third-party user who 'just discovered' a blog.
5. CONCISE AND ACTIONABLE: Aim for 200 to 400 words of crisp, insightful breakdown.

{link_instructions}

Respond strictly in this JSON format:
{{
  "answer_text": "Your direct, comprehensive markdown response here...",
  "optional_resource_sentence": "{example_resource}",
  "link_rationale": "{example_rationale}"
}}
"""
        provider = get_default_provider()
        req = LLMRequest(
            prompt=prompt,
            role=LLMRole.WRITING,
            temperature=0.4,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        try:
            resp = await provider.generate(req)
            data = json.loads(resp.content.strip())

            answer = str(data.get("answer_text", "")).strip()
            resource_sentence = str(data.get("optional_resource_sentence") or "").strip() if allow_link else ""
            link_rationale = str(data.get("link_rationale") or "")

            if not answer:
                answer = f"To address **{question_title.rstrip('?')}**, the primary considerations center around structured execution, proper boundaries, and practical application."

            # Assemble full markdown
            if allow_link and article_url and resource_sentence:
                full_md = f"{answer}\n\n---\n\n*{resource_sentence}*"
                response_type = RedditResponseType.ANSWER_WITH_OPTIONAL_RESOURCE.value
                included_link = article_url
            else:
                full_md = answer
                response_type = RedditResponseType.ANSWER_ONLY.value
                included_link = None

            return GeneratedRedditResponse(
                response_type=response_type,
                answer_text=answer,
                optional_resource_sentence=resource_sentence if allow_link else None,
                full_markdown=full_md,
                included_link=included_link,
                link_rationale=link_rationale,
            )

        except Exception as exc:
            logger.warning("LLM response generation failed (%s); using deterministic template", exc)
            fallback_answer = (
                f"Regarding **{question_title.rstrip('?')}**:\n\n"
                "- **Key Concept**: Focus on first-principles understanding rather than relying on surface-level shortcuts.\n"
                "- **Practical Approach**: Break the challenge into smaller testable steps and verify outcomes systematically.\n"
                "- **Long-term Strategy**: Build habits that reinforce critical thinking alongside automated tools."
            )
            return GeneratedRedditResponse(
                response_type=RedditResponseType.ANSWER_ONLY.value,
                answer_text=fallback_answer,
                optional_resource_sentence=None,
                full_markdown=fallback_answer,
                included_link=None,
                link_rationale="Fallback answer generated without external links.",
            )
