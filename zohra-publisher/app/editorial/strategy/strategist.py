"""
Zohra — Content Strategist (Part 5).

Translates Part 4 ResearchPackage and Part 3 Opportunity into an actionable editorial strategy:
defines reader problem, search intent architecture, angle refinement, information gain strategy,
target audience adaptation, and depth guidelines.
"""

from __future__ import annotations

from app.schemas.editorial import ContentStrategyData, ContentType, PrimaryIntent
from app.schemas.research import FinalResearchPackage


class ContentStrategist:
    """Builds a structured editorial strategy before any prose generation."""

    INTENT_TYPE_MAP: dict[str, str] = {
        PrimaryIntent.NEWS.value: ContentType.NEWS_ANALYSIS.value,
        PrimaryIntent.TUTORIAL.value: ContentType.TUTORIAL.value,
        PrimaryIntent.COMPARISON.value: ContentType.COMPARISON.value,
        PrimaryIntent.COMMERCIAL_INVESTIGATION.value: ContentType.COMPARISON.value,
        PrimaryIntent.TRANSACTIONAL.value: ContentType.PRICING.value,
        PrimaryIntent.TROUBLESHOOTING.value: ContentType.TROUBLESHOOTING.value,
        PrimaryIntent.REFERENCE.value: ContentType.REFERENCE.value,
        PrimaryIntent.INFORMATIONAL.value: ContentType.EXPLAINER.value,
    }

    LENGTH_RANGES: dict[str, tuple[int, int]] = {
        ContentType.BREAKING_NEWS.value: (400, 800),
        ContentType.NEWS_ANALYSIS.value: (800, 1400),
        ContentType.PRICING.value: (900, 1600),
        ContentType.EXPLAINER.value: (1000, 1800),
        ContentType.TUTORIAL.value: (1200, 2200),
        ContentType.TROUBLESHOOTING.value: (800, 1600),
        ContentType.COMPARISON.value: (1400, 2600),
        ContentType.GUIDE.value: (1600, 3000),
        ContentType.REVIEW.value: (1200, 2200),
        ContentType.REFERENCE.value: (800, 1500),
        ContentType.FAQ.value: (600, 1200),
    }

    @classmethod
    def develop_strategy(
        cls,
        research_pkg: FinalResearchPackage,
        primary_keyword: str,
        search_intent: str,
        proposed_angle: str | None = None,
        target_audience: list[str] | None = None,
        content_type_override: str | None = None,
        tone_override: str | None = None,
    ) -> ContentStrategyData:
        """Constructs the editorial strategy based on verified research and search intent."""
        # 1. Determine Content Type
        norm_intent = search_intent.lower().strip()
        if content_type_override:
            rec_content_type = content_type_override
        else:
            rec_content_type = cls.INTENT_TYPE_MAP.get(norm_intent, ContentType.EXPLAINER.value)
            # Refine if topic explicitly mentions pricing, comparison, vs, or tutorial
            kw_lower = primary_keyword.lower()
            if "pricing" in kw_lower or "cost" in kw_lower or "price" in kw_lower:
                rec_content_type = ContentType.PRICING.value
            elif " vs " in kw_lower or " versus " in kw_lower or "alternative" in kw_lower:
                rec_content_type = ContentType.COMPARISON.value
            elif "how to" in kw_lower or "tutorial" in kw_lower or "guide" in kw_lower:
                rec_content_type = ContentType.TUTORIAL.value
            elif "review" in kw_lower:
                rec_content_type = ContentType.REVIEW.value

        # 2. Formulate Reader Problem & Job-to-be-Done
        topic = research_pkg.topic
        audience_str = ", ".join(target_audience) if target_audience else "curious practitioners and decision-makers"

        if rec_content_type == ContentType.PRICING.value:
            reader_problem = (
                f"The reader needs transparent, up-to-date pricing, plan tiers, and practical limitations for {topic} "
                f"to determine budget fit without encountering hidden costs."
            )
            reader_goal = f"Quickly understand current costs, plan tiers, limits, and choose the most cost-effective option for {topic}."
            content_goal = f"Deliver verified pricing breakdown, tier comparison, and practical decision rules for {topic}."
        elif rec_content_type == ContentType.TUTORIAL.value:
            reader_problem = (
                f"The reader wants actionable, step-by-step guidance on implementing or utilizing {topic} "
                f"without running into undocumented roadblocks or configuration errors."
            )
            reader_goal = f"Successfully set up and execute the workflow for {topic} with verified steps and troubleshooting solutions."
            content_goal = f"Provide structured prerequisites, step-by-step instructions, and error mitigation for {topic}."
        elif rec_content_type == ContentType.COMPARISON.value:
            reader_problem = (
                f"The reader is evaluating {topic} against key alternatives and needs a neutral, evidence-grounded comparison "
                f"of features, pricing, and limitations rather than marketing hype."
            )
            reader_goal = "Determine which solution best fits their specific workflow, constraints, and budget."
            content_goal = "Examine verified trade-offs, benchmarks, and suitability criteria across options."
        elif rec_content_type in (ContentType.NEWS_ANALYSIS.value, ContentType.BREAKING_NEWS.value):
            reader_problem = (
                f"The reader needs verified facts regarding recent developments in {topic}, what was officially confirmed, "
                f"and how it impacts their operations."
            )
            reader_goal = "Understand what happened, when it occurred, who is affected, and what remains unverified."
            content_goal = f"Provide a verified timeline, official statements, and clear impact analysis for {topic}."
        else:
            reader_problem = (
                f"The reader seeks a clear, comprehensive understanding of {topic}, including capabilities, "
                f"practical constraints, and real-world implications."
            )
            reader_goal = f"Master the core concepts, documented capabilities, and current status of {topic}."
            content_goal = f"Deliver an authoritative, evidence-backed overview answering key questions for {topic}."

        # 3. Angle Refinement
        # Incorporate verified facts into the angle without drifting intent
        refined_angle = proposed_angle or f"Complete, evidence-backed guide to {topic}"
        if research_pkg.verified_facts:
            # Check for unique factual highlights (e.g. pricing, major features)
            feature_facts = [f for f in research_pkg.verified_facts if f.claim_type in ("capability", "price")]
            if feature_facts and not proposed_angle:
                highlight = feature_facts[0].claim
                refined_angle = f"{topic}: Key capabilities, verified details ({highlight[:50]}...), and practical guide for {audience_str}"

        # 4. Differentiation & Information Gain Strategy
        diff_points = []
        if research_pkg.primary_sources:
            diff_points.append("Direct primary-source documentation citations instead of generic hearsay")
        if research_pkg.important_numbers:
            diff_points.append("Concrete verified metrics and pricing numbers")
        if research_pkg.limitations:
            diff_points.append("Explicit, transparent coverage of known technical limitations and constraints")
        if research_pkg.timeline:
            diff_points.append("Structured chronological timeline of developments")

        diff_strategy = "; ".join(diff_points) if diff_points else "Comprehensive multi-source factual synthesis"

        info_gain = (
            f"Combines verified facts from {len(research_pkg.primary_sources)} primary sources and "
            f"{len(research_pkg.supporting_sources)} supporting sources. "
            f"Fills existing gaps: explicitly addresses limitations ({len(research_pkg.limitations)} identified) "
            f"and provides clear answers to {len(research_pkg.research_questions.answered)} core reader questions."
        )

        # 5. Tone & Depth
        tone = tone_override or "authoritative_approachable"
        depth = "deep" if len(research_pkg.verified_facts) > 10 else "comprehensive"

        # 6. Length Bounds
        l_min, l_max = cls.LENGTH_RANGES.get(rec_content_type, (1000, 1800))
        if depth == "deep":
            l_min += 200
            l_max += 400

        return ContentStrategyData(
            reader_problem=reader_problem,
            reader_goal=reader_goal,
            search_intent=norm_intent,
            content_goal=content_goal,
            recommended_content_type=rec_content_type,
            angle=refined_angle,
            differentiation_strategy=diff_strategy,
            information_gain_strategy=info_gain,
            tone=tone,
            depth=depth,
            target_length_min=l_min,
            target_length_max=l_max,
            conversion_goal="Equip reader with verified decision confidence",
            risk_notes="; ".join(research_pkg.risk_flags) if research_pkg.risk_flags else None,
        )
