"""
Zohra — Section Writer (Part 5).

Generates evidence-grounded prose for individual blueprint sections using bounded context:
enforces safe-claim boundaries, mandatory attributions, explicit temporal scoping,
and specialized formats (prose, list, steps, table, comparison, pricing, news).
"""

from __future__ import annotations

from typing import Any

from app.editorial.writer.review_guard import ReviewRestrictionGuard
from app.schemas.editorial import DraftSection, SectionBlueprint
from app.schemas.research import FinalResearchPackage, VerifiedFactHandoff


class SectionWriter:
    """Renders section prose strictly within supplied claim and evidence boundaries."""

    @classmethod
    def write_section(
        cls,
        section_bp: SectionBlueprint,
        allocated_facts: list[VerifiedFactHandoff],
        research_pkg: FinalResearchPackage,
        brand_tone: str = "authoritative_approachable",
    ) -> DraftSection:
        """Writes a single section using only allocated facts and explicit research context."""
        sec_id = section_bp.section_id
        heading = section_bp.heading
        rec_format = section_bp.recommended_format

        citation_placements: list[dict[str, Any]] = []
        used_claim_ids: list[str] = []
        paragraphs: list[str] = []

        # 1. Lead sentence answering reader question directly
        lead_sentence = f"To address whether and how {section_bp.reader_question.lower().rstrip('?')}, documented evidence provides clear guidance."
        if allocated_facts:
            first_fact = allocated_facts[0]
            if first_fact.attribution_required:
                lead_sentence = f"According to released documentation and official statements, {first_fact.claim}."
            else:
                lead_sentence = f"{first_fact.claim}."
            used_claim_ids.append(first_fact.claim_id)
            src_ids = research_pkg.citation_map.get(first_fact.claim_id, [])
            citation_placements.append({
                "claim_id": first_fact.claim_id,
                "source_ids": src_ids,
                "placement_offset": len(lead_sentence),
            })

        paragraphs.append(lead_sentence)

        # 2. Body composition based on format
        if rec_format == "steps":
            paragraphs.append("Follow these verified implementation steps:")
            step_idx = 1
            for fact in allocated_facts[1:]:
                statement = fact.claim
                if fact.attribution_required:
                    statement = f"According to documentation, {statement}"
                paragraphs.append(f"{step_idx}. **{fact.claim_type.title()}**: {statement}.")
                used_claim_ids.append(fact.claim_id)
                step_idx += 1
                src_ids = research_pkg.citation_map.get(fact.claim_id, [])
                citation_placements.append({
                    "claim_id": fact.claim_id,
                    "source_ids": src_ids,
                    "placement_offset": len(paragraphs[-1]),
                })
        elif rec_format == "list":
            for fact in allocated_facts[1:]:
                statement = fact.claim
                if fact.attribution_required:
                    statement = f"According to reported documentation, {statement}"
                paragraphs.append(f"- **{fact.subject or fact.claim_type.title()}**: {statement}.")
                used_claim_ids.append(fact.claim_id)
                src_ids = research_pkg.citation_map.get(fact.claim_id, [])
                citation_placements.append({
                    "claim_id": fact.claim_id,
                    "source_ids": src_ids,
                    "placement_offset": len(paragraphs[-1]),
                })
        else:
            # Prose format
            body_sentences = []
            for fact in allocated_facts[1:]:
                statement = fact.claim
                # Temporal language for time-sensitive facts
                if fact.time_sensitive:
                    statement = f"As of the latest documentation, {statement}"
                elif fact.attribution_required:
                    statement = f"Company documentation reports that {statement}"

                body_sentences.append(f"{statement}.")
                used_claim_ids.append(fact.claim_id)
                src_ids = research_pkg.citation_map.get(fact.claim_id, [])
                citation_placements.append({
                    "claim_id": fact.claim_id,
                    "source_ids": src_ids,
                    "placement_offset": len(statement),
                })

            if body_sentences:
                paragraphs.append(" ".join(body_sentences))

        # Check for limitations if this is sec_limitations
        if sec_id == "sec_limitations" and research_pkg.limitations:
            for lim in research_pkg.limitations:
                lim_text = lim if isinstance(lim, str) else str(lim)
                paragraphs.append(f"- **Documented Limitation**: {lim_text}.")

        raw_content = "\n\n".join(paragraphs)

        # 3. Sanitize against unauthorized fake first-hand testing claims
        clean_content, _ = ReviewRestrictionGuard.sanitize_text(raw_content)

        return DraftSection(
            section_id=sec_id,
            heading=heading,
            content=clean_content,
            used_claim_ids=used_claim_ids,
            citation_placements=citation_placements,
            unresolved_issues=[],
        )
