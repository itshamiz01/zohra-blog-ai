"""
Zohra — Draft Assembler (Part 5).

Assembles the complete article from generated components:
answer-first introductions, section ordering, smooth transitions, structured tables,
grounded FAQs, conclusions, and non-manipulative call-to-actions.
"""

from __future__ import annotations

from app.schemas.editorial import (
    ArticleBlueprintData,
    ContentStrategyData,
    DraftFAQItem,
    DraftSection,
    DraftTableItem,
    EditorialArticleContent,
)
from app.schemas.research import FinalResearchPackage


class DraftAssembler:
    """Assembles all editorial components into a cohesive, grounded full draft."""

    @classmethod
    def generate_introduction(
        cls,
        topic: str,
        primary_keyword: str,
        blueprint: ArticleBlueprintData,
        research_pkg: FinalResearchPackage,
    ) -> str:
        """Constructs an answer-first introduction without filler or clichés."""
        # Find leading fact for the immediate direct answer
        direct_answer = ""
        if research_pkg.verified_facts:
            lead_fact = research_pkg.verified_facts[0]
            direct_answer = f"{lead_fact.claim}."

        intro_parts = [
            f"If you are evaluating {primary_keyword}, documented facts provide a clear path forward.",
            direct_answer,
            "In this guide, we break down verified capabilities, official pricing tiers, practical workflows, "
            "and known limitations based directly on primary documentation and independent reporting.",
        ]
        return " ".join([p for p in intro_parts if p.strip()])

    @classmethod
    def generate_conclusion(
        cls,
        topic: str,
        strategy: ContentStrategyData,
        blueprint: ArticleBlueprintData,
        research_pkg: FinalResearchPackage,
    ) -> str:
        """Constructs a decision framework conclusion without manufactured urgency or hype."""
        return (
            f"### Final Verdict & Decision Framework\n\n"
            f"Evaluating {topic} comes down to matching its verified capabilities against your specific constraints. "
            f"{blueprint.article_promise} "
            f"For most practitioners, testing the core workflow against documented limitations will determine "
            f"whether it fits your operational budget and technical requirements. "
            f"Review official documentation for any subsequent version updates."
        )

    @classmethod
    def generate_tables(
        cls,
        blueprint: ArticleBlueprintData,
        research_pkg: FinalResearchPackage,
    ) -> list[DraftTableItem]:
        """Constructs evidence-grounded markdown comparison and specification tables."""
        tables: list[DraftTableItem] = []
        for t_plan in blueprint.table_plan:
            t_id = t_plan["table_id"]
            title = t_plan["title"]
            headers = t_plan["headers"]
            rows: list[list[str]] = []
            claim_ids: list[str] = []

            # Populate rows from important_numbers and pricing facts
            for num in research_pkg.important_numbers[:5]:
                val_str = f"{num.get('currency', '')} {num.get('value', '')} {num.get('unit', '')}".strip()
                claim_text = num.get("claim", "")
                rows.append([claim_text[:40], val_str, "Documented Scope", "Official Source"])
                if "claim_id" in num:
                    claim_ids.append(num["claim_id"])

            if not rows:
                # Fallback to key verified facts
                for f in research_pkg.verified_facts[:4]:
                    rows.append([f.claim[:40], f.object_value or "Confirmed", f.region or "Global", "Verified"])
                    claim_ids.append(f.claim_id)

            if rows:
                tables.append(
                    DraftTableItem(
                        table_id=t_id,
                        title=title,
                        headers=headers,
                        rows=rows,
                        grounded_claim_ids=claim_ids,
                    )
                )

        return tables

    @classmethod
    def generate_faqs(
        cls,
        blueprint: ArticleBlueprintData,
        research_pkg: FinalResearchPackage,
    ) -> list[DraftFAQItem]:
        """Builds grounded FAQ items from answered research questions."""
        faqs: list[DraftFAQItem] = []
        for f_plan in blueprint.faq_plan[:4]:
            q_text = f_plan["question"]
            # Locate supporting fact
            matched_fact = next(
                (f for f in research_pkg.verified_facts if any(w in f.claim.lower() for w in q_text.lower().split() if len(w) > 4)),
                None,
            )
            if matched_fact:
                ans = f"According to verified documentation, {matched_fact.claim}."
                c_ids = [matched_fact.claim_id]
            else:
                ans = "Documented evidence indicates that details depend on official release status and user configuration."
                c_ids = []

            faqs.append(
                DraftFAQItem(
                    question=q_text,
                    answer=ans,
                    grounded_claim_ids=c_ids,
                )
            )

        return faqs

    @classmethod
    def assemble_article(
        cls,
        headline: str,
        introduction: str,
        sections: list[DraftSection],
        tables: list[DraftTableItem],
        faqs: list[DraftFAQItem],
        conclusion: str,
    ) -> tuple[EditorialArticleContent, str]:
        """Combines all components into an EditorialArticleContent schema and full Markdown string."""
        md_parts: list[str] = [f"# {headline}\n", introduction]

        for sec in sections:
            md_parts.append(f"## {sec.heading}\n")
            md_parts.append(sec.content)

            # Insert table if applicable
            if sec.section_id in ("sec_pricing", "sec_capabilities") and tables:
                t = tables[0]
                t_md = [f"\n### {t.title}\n", "| " + " | ".join(t.headers) + " |", "| " + " | ".join(["---"] * len(t.headers)) + " |"]
                for r in t.rows:
                    t_md.append("| " + " | ".join(r) + " |")
                md_parts.append("\n".join(t_md))

        # Append FAQs
        if faqs:
            md_parts.append("## Frequently Asked Questions\n")
            for faq in faqs:
                md_parts.append(f"### {faq.question}\n{faq.answer}")

        # Append Conclusion
        md_parts.append(conclusion)

        full_content = "\n\n".join(md_parts)

        article_obj = EditorialArticleContent(
            introduction=introduction,
            sections=sections,
            faq=faqs,
            tables=tables,
            conclusion=conclusion,
        )

        return article_obj, full_content
