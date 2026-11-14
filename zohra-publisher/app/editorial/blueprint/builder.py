"""
Zohra — Article Blueprint Builder (Part 5).

Constructs the structural blueprint of the article prior to any prose generation:
defines the article promise, sections, claim allocation, citation requirements,
FAQ plans, and structured table specifications.
"""

from __future__ import annotations

from typing import Any

from app.schemas.editorial import (
    ArticleBlueprintData,
    ContentStrategyData,
    ContentType,
    SectionBlueprint,
)
from app.schemas.research import FinalResearchPackage


class ArticleBlueprintBuilder:
    """Builds an evidence-grounded structural blueprint for an article."""

    @classmethod
    def build_blueprint(
        cls,
        research_pkg: FinalResearchPackage,
        strategy: ContentStrategyData,
        primary_keyword: str,
        secondary_keywords: list[str] | None = None,
        target_audience: str | None = None,
    ) -> ArticleBlueprintData:
        sec_kw = secondary_keywords or []
        topic = research_pkg.topic
        content_type = strategy.recommended_content_type

        # 1. Formulate Working Title & Article Promise
        working_title = f"{topic}: The Complete Evidence-Based Guide"
        if content_type == ContentType.PRICING.value:
            working_title = f"{topic} Pricing & Plans: Full Breakdown and Limits"
            promise = f"Understand {topic}'s current pricing plans, hidden limits, and choose the right tier for your budget."
        elif content_type == ContentType.TUTORIAL.value:
            working_title = f"How to Use {topic}: Step-by-Step Setup & Workflow Guide"
            promise = f"Successfully set up and operate {topic} with verified step-by-step instructions and best practices."
        elif content_type == ContentType.COMPARISON.value:
            working_title = f"{topic} Comparison: Features, Pricing, and Trade-offs"
            promise = f"Evaluate {topic} against realistic alternatives based on verified specifications and practical trade-offs."
        elif content_type in (ContentType.NEWS_ANALYSIS.value, ContentType.BREAKING_NEWS.value):
            working_title = f"{topic}: Verified Updates, Impact, and What Comes Next"
            promise = f"Understand the latest verified developments concerning {topic} and what is officially confirmed."
        else:
            working_title = f"What Is {topic}? Capabilities, Specifications, and Practical Overview"
            promise = f"Master the core capabilities, verified facts, and real-world considerations for {topic}."

        introduction_goal = (
            f"Provide an immediate, direct answer to the reader's primary query regarding '{primary_keyword}', "
            f"frame the practical context for {target_audience or 'practitioners'}, and preview the verified findings."
        )
        conclusion_goal = (
            f"Synthesize the key takeaways for {topic}, provide an objective decision framework without artificial hype, "
            f"and outline logical next steps."
        )

        # 2. Allocate Claims to Sections
        # Sort claims by type
        pricing_claims = [f for f in research_pkg.verified_facts if f.claim_type == "price" or "price" in f.claim.lower() or "cost" in f.claim.lower()]
        capability_claims = [f for f in research_pkg.verified_facts if f.claim_type == "capability"]
        date_claims = [f for f in research_pkg.verified_facts if f.claim_type in ("date", "availability", "timeline")]
        general_facts = [f for f in research_pkg.verified_facts if f not in pricing_claims and f not in capability_claims and f not in date_claims]

        sections: list[SectionBlueprint] = []
        claim_allocation: dict[str, list[str]] = {}

        # Section 1: Overview & Core Concept
        sec1_claims = [f.claim_id for f in general_facts[:3]]
        sec1_target_kw = [primary_keyword]
        sections.append(
            SectionBlueprint(
                section_id="sec_overview",
                heading=f"What Is {topic} and How Does It Work?",
                purpose=f"Define {topic}, establish baseline context, and explain its foundational architecture.",
                reader_question=f"What exactly is {topic} and what core problem does it address?",
                target_claim_ids=sec1_claims,
                supporting_claim_ids=[],
                target_keywords=sec1_target_kw,
                recommended_format="prose",
                estimated_length=300,
                citation_requirement=True,
            )
        )
        claim_allocation["sec_overview"] = sec1_claims

        # Section 2: Key Capabilities & Features
        sec2_claims = [f.claim_id for f in capability_claims]
        sec2_kw = [k for k in sec_kw if "feature" in k.lower() or "capability" in k.lower() or "spec" in k.lower()]
        sections.append(
            SectionBlueprint(
                section_id="sec_capabilities",
                heading=f"Core Features & Documented Capabilities of {topic}",
                purpose="Detail verified technical specifications, supported formats, and performance metrics.",
                reader_question=f"What can {topic} actually do according to documented evidence?",
                target_claim_ids=sec2_claims,
                supporting_claim_ids=[],
                target_keywords=sec2_kw or [f"{primary_keyword} features"],
                recommended_format="list" if len(sec2_claims) > 3 else "prose",
                estimated_length=400,
                citation_requirement=True,
            )
        )
        claim_allocation["sec_capabilities"] = sec2_claims

        # Section 3: Pricing & Availability (if pricing claims exist or pricing intent)
        if pricing_claims or content_type == ContentType.PRICING.value or any("price" in k.lower() for k in sec_kw):
            sec3_claims = [f.claim_id for f in pricing_claims]
            sections.append(
                SectionBlueprint(
                    section_id="sec_pricing",
                    heading=f"{topic} Pricing, Plans, and Tier Limits",
                    purpose="Break down official subscription tiers, currency costs, quotas, and free tier availability.",
                    reader_question=f"How much does {topic} cost and what limits apply to each tier?",
                    target_claim_ids=sec3_claims,
                    supporting_claim_ids=[],
                    target_keywords=[k for k in sec_kw if "price" in k.lower() or "cost" in k.lower()] or [f"{primary_keyword} pricing"],
                    recommended_format="table" if research_pkg.important_numbers else "prose",
                    estimated_length=350,
                    citation_requirement=True,
                )
            )
            claim_allocation["sec_pricing"] = sec3_claims

        # Section 4: Workflow / Practical Application
        if content_type == ContentType.TUTORIAL.value:
            sec4_claims = [f.claim_id for f in general_facts[3:6]]
            sections.append(
                SectionBlueprint(
                    section_id="sec_workflow",
                    heading=f"Step-by-Step Implementation & Workflow for {topic}",
                    purpose="Provide ordered execution steps, prerequisites, and expected outcomes.",
                    reader_question=f"How do I set up and execute the workflow for {topic}?",
                    target_claim_ids=sec4_claims,
                    supporting_claim_ids=[],
                    target_keywords=[k for k in sec_kw if "step" in k.lower() or "how" in k.lower()],
                    recommended_format="steps",
                    estimated_length=450,
                    citation_requirement=True,
                )
            )
            claim_allocation["sec_workflow"] = sec4_claims

        # Section 5: Documented Limitations & Constraints
        sec5_claims = [f.claim_id for f in research_pkg.verified_facts if f.claim_type == "limitation"]
        sections.append(
            SectionBlueprint(
                section_id="sec_limitations",
                heading="Known Limitations & Practical Constraints",
                purpose="Disclose documented technical boundaries, hardware requirements, or operational constraints.",
                reader_question=f"What are the documented limitations or drawbacks of {topic}?",
                target_claim_ids=sec5_claims,
                supporting_claim_ids=[],
                target_keywords=[f"{primary_keyword} limitations"],
                recommended_format="list",
                estimated_length=300,
                citation_requirement=True,
            )
        )
        claim_allocation["sec_limitations"] = sec5_claims

        # 3. FAQ Plan
        faq_plan: list[dict[str, Any]] = []
        for q_text in research_pkg.research_questions.answered[:4]:
            faq_plan.append({
                "question": q_text if isinstance(q_text, str) else q_text.get("question", str(q_text)),
                "source_requirement": "grounded",
            })

        # 4. Table Plan
        table_plan: list[dict[str, Any]] = []
        if research_pkg.important_numbers or pricing_claims:
            table_plan.append({
                "table_id": "tbl_pricing_summary",
                "title": f"{topic} Pricing & Specifications Matrix",
                "headers": ["Plan / Specification", "Verified Value", "Scope / Region", "Source Reference"],
                "section_id": "sec_pricing" if "sec_pricing" in claim_allocation else "sec_capabilities",
            })

        # 5. Citation Plan
        citation_plan: list[dict[str, Any]] = []
        for c_id, src_ids in research_pkg.citation_map.items():
            citation_plan.append({
                "claim_id": c_id,
                "preferred_source_ids": src_ids,
                "is_primary_preferred": True,
            })

        return ArticleBlueprintData(
            working_title=working_title,
            article_promise=promise,
            primary_intent=strategy.search_intent,
            content_type=content_type,
            target_audience=target_audience,
            introduction_goal=introduction_goal,
            sections=sections,
            conclusion_goal=conclusion_goal,
            faq_plan=faq_plan,
            table_plan=table_plan,
            citation_plan=citation_plan,
            internal_link_plan=[],
            claim_allocation=claim_allocation,
        )
