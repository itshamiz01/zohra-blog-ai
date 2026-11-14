"""
Zohra — Editorial Generation & Drafting Pipeline Orchestrator (Part 5).

Coordinates the complete evidence-grounded editorial workflow:
Validates Part 4 Research Package -> Builds Strategy -> Generates Blueprint & Allocates Claims
-> Renders Bounded Sections -> Assembles Article -> Applies Brand Voice & SEO Optimization
-> Verifies Sentence Grounding -> Scores Quality -> Targeted Revisions -> Assembles Final Package.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.article_blueprints import ArticleBlueprint
from app.db.models.brand_voice_profiles import BrandVoiceProfile
from app.db.models.content_strategies import ContentStrategy
from app.db.models.draft_claim_usage import DraftClaimUsage
from app.db.models.draft_projects import DraftProject, DraftProjectStatus
from app.db.models.draft_versions import DraftVersion
from app.db.models.editorial_draft_packages import EditorialDraftPackage
from app.db.models.headline_candidates import HeadlineCandidate
from app.db.models.internal_link_candidates import InternalLinkCandidate
from app.db.models.research_followup_requests import ResearchFollowupRequest
from app.db.models.research_packages import ResearchPackage
from app.db.models.sentence_grounding import SentenceGrounding
from app.editorial.blueprint.builder import ArticleBlueprintBuilder
from app.editorial.claims.allocator import ClaimAllocator
from app.editorial.grounding.verifier import GroundingVerifier
from app.editorial.headline.engine import HeadlineEngine
from app.editorial.links.internal_links import InternalLinkPlanner
from app.editorial.multilingual.engine import MultilingualEngine
from app.editorial.quality.scorer import DraftQualityScorer
from app.editorial.research_loop.followup import ResearchFollowupHandler
from app.editorial.revision.engine import RevisionEngine
from app.editorial.seo.optimizer import SemanticSEOOptimizer
from app.editorial.strategy.strategist import ContentStrategist
from app.editorial.voice.brand_voice import BrandVoiceEngine
from app.editorial.writer.assembly import DraftAssembler
from app.editorial.writer.section_writer import SectionWriter
from app.schemas.editorial import (
    BrandVoiceProfileResponse,
    DraftSection,
    EditorialDraftPackageData,
)
from app.schemas.research import FinalResearchPackage

logger = logging.getLogger(__name__)


class EditorialPipeline:
    """Master orchestrator for the Part 5 Editorial Drafting Engine."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute_draft_project(
        self,
        draft_project_id: uuid.UUID,
        brand_voice_id: uuid.UUID | None = None,
        existing_site_content: list[dict[str, Any]] | None = None,
    ) -> EditorialDraftPackageData | None:
        """Executes the full end-to-end editorial drafting pipeline."""
        # 1. Load DraftProject
        stmt = select(DraftProject).where(DraftProject.id == draft_project_id)
        res = await self.session.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"DraftProject {draft_project_id} not found.")

        project.status = DraftProjectStatus.STRATEGIZING.value
        project.started_at = datetime.now(UTC)
        await self.session.commit()

        # 2. Load Part 4 ResearchPackage
        pkg_stmt = select(ResearchPackage).where(ResearchPackage.id == project.research_package_id)
        pkg_res = await self.session.execute(pkg_stmt)
        db_pkg = pkg_res.scalar_one_or_none()
        if not db_pkg:
            project.status = DraftProjectStatus.FAILED.value
            project.stop_reason = f"ResearchPackage {project.research_package_id} not found."
            await self.session.commit()
            return None

        # Build FinalResearchPackage schema from DB record
        research_pkg = FinalResearchPackage(
            research_project_id=str(db_pkg.research_project_id),
            opportunity_id=str(db_pkg.opportunity_id),
            topic=db_pkg.topic,
            research_objective=db_pkg.research_objective,
            executive_summary=db_pkg.executive_summary,
            verified_facts=db_pkg.verified_facts_json or [],
            uncertain_claims=db_pkg.uncertain_claims_json or [],
            contradictions=db_pkg.contradictions_json or [],
            timeline=db_pkg.timeline_json or [],
            entities=db_pkg.entities_json or [],
            primary_sources=db_pkg.primary_sources_json or [],
            supporting_sources=db_pkg.supporting_sources_json or [],
            research_questions={
                "answered": db_pkg.questions_answered_json or [],
                "partially_answered": [],
                "unanswered": db_pkg.questions_unanswered_json or [],
            },
            content_gaps=db_pkg.content_gaps_json or [],
            important_numbers=db_pkg.important_numbers_json or [],
            important_dates=db_pkg.important_dates_json or [],
            limitations=db_pkg.limitations_json or [],
            risk_flags=db_pkg.risk_flags_json or [],
            research_quality_score=db_pkg.research_quality_score,
            research_confidence_score=db_pkg.research_confidence_score,
            source_quality_score=90.0,
            critical_claim_coverage_score=100.0,
            instructions_for_writer={
                "safe_claim_ids": [f["claim_id"] for f in (db_pkg.verified_facts_json or []) if f.get("writer_policy") == "safe_to_state_as_fact"],
                "attribution_required_claim_ids": [f["claim_id"] for f in (db_pkg.verified_facts_json or []) if f.get("attribution_required")],
                "do_not_state_as_fact_claim_ids": [c.get("claim_id", "") for c in (db_pkg.uncertain_claims_json or [])],
                "time_sensitive_claim_ids": [f["claim_id"] for f in (db_pkg.verified_facts_json or []) if f.get("time_sensitive")],
            },
            citation_map={
                f["claim_id"]: [e["source_id"] for e in f.get("evidence", []) if "source_id" in e]
                for f in (db_pkg.verified_facts_json or [])
            },
        )

        project.research_quality_score = research_pkg.research_quality_score

        # 3. RESEARCH QUALITY GATE (Section 7)
        is_high_risk = bool(research_pkg.risk_flags)
        min_required_quality = 90.0 if is_high_risk else 75.0

        if research_pkg.research_quality_score < min_required_quality:
            project.status = DraftProjectStatus.NEEDS_RESEARCH.value
            project.stop_reason = (
                f"Research quality score ({research_pkg.research_quality_score:.1f}) is below the required "
                f"threshold ({min_required_quality:.1f})."
            )
            await self.session.commit()
            return None

        # 4. CONTENT STRATEGY (Section 9-18)
        strategy_data = ContentStrategist.develop_strategy(
            research_pkg=research_pkg,
            primary_keyword=project.primary_keyword,
            search_intent=project.primary_intent,
            target_audience=project.target_audience,
            content_type_override=project.content_type,
        )

        # Check for missing critical facts (Section 137-138)
        missing_facts = ResearchFollowupHandler.identify_missing_critical_facts(research_pkg, strategy_data)
        if missing_facts:
            for mf in missing_facts:
                rf_req = ResearchFollowupRequest(
                    draft_project_id=project.id,
                    research_project_id=uuid.UUID(research_pkg.research_project_id),
                    question=mf["question"],
                    reason=mf["reason"],
                    priority=mf["priority"],
                    status="pending",
                )
                self.session.add(rf_req)

            project.status = DraftProjectStatus.NEEDS_RESEARCH.value
            project.stop_reason = f"Drafting stopped due to {len(missing_facts)} missing critical facts."
            await self.session.commit()
            return None

        # Persist ContentStrategy
        db_strategy = ContentStrategy(
            draft_project_id=project.id,
            reader_problem=strategy_data.reader_problem,
            reader_goal=strategy_data.reader_goal,
            search_intent=strategy_data.search_intent,
            content_goal=strategy_data.content_goal,
            recommended_content_type=strategy_data.recommended_content_type,
            angle=strategy_data.angle,
            differentiation_strategy=strategy_data.differentiation_strategy,
            information_gain_strategy=strategy_data.information_gain_strategy,
            tone=strategy_data.tone,
            depth=strategy_data.depth,
            target_length_min=strategy_data.target_length_min,
            target_length_max=strategy_data.target_length_max,
            conversion_goal=strategy_data.conversion_goal,
            risk_notes=strategy_data.risk_notes,
        )
        self.session.add(db_strategy)
        await self.session.commit()

        # 5. BLUEPRINTING (Section 19-24)
        project.status = DraftProjectStatus.BLUEPRINTING.value
        await self.session.commit()

        blueprint_data = ArticleBlueprintBuilder.build_blueprint(
            research_pkg=research_pkg,
            strategy=strategy_data,
            primary_keyword=project.primary_keyword,
            target_audience=", ".join(project.target_audience) if project.target_audience else None,
        )

        # Allocate claims
        allocation_result = ClaimAllocator.allocate_claims(research_pkg, blueprint_data)

        # Persist Blueprint & Claim Usages
        db_blueprint = ArticleBlueprint(
            draft_project_id=project.id,
            working_title=blueprint_data.working_title,
            article_promise=blueprint_data.article_promise,
            primary_intent=blueprint_data.primary_intent,
            content_type=blueprint_data.content_type,
            target_audience=blueprint_data.target_audience,
            introduction_goal=blueprint_data.introduction_goal,
            sections_json=[s.dict() for s in blueprint_data.sections],
            conclusion_goal=blueprint_data.conclusion_goal,
            faq_plan_json=blueprint_data.faq_plan,
            table_plan_json=blueprint_data.table_plan,
            citation_plan_json=blueprint_data.citation_plan,
            claim_allocation_json=blueprint_data.claim_allocation,
        )
        self.session.add(db_blueprint)

        for sec_id, facts in allocation_result.allocated_claims.items():
            for f in facts:
                dcu = DraftClaimUsage(
                    draft_project_id=project.id,
                    claim_id=f.claim_id,
                    section_id=sec_id,
                    usage_type="primary",
                    required=True,
                    used=True,
                    citation_required=f.attribution_required,
                )
                self.session.add(dcu)

        # 6. HEADLINES (Section 33-37)
        headline_candidates = HeadlineEngine.generate_candidates(
            topic=research_pkg.topic,
            primary_keyword=project.primary_keyword,
            strategy=strategy_data,
            draft_project_id=project.id,
        )
        winning_headline = headline_candidates[0].headline if headline_candidates else blueprint_data.working_title
        for hc in headline_candidates:
            db_hc = HeadlineCandidate(
                draft_project_id=project.id,
                headline=hc.headline,
                style=hc.style,
                intent_score=hc.intent_score,
                clarity_score=hc.clarity_score,
                accuracy_score=hc.accuracy_score,
                seo_score=hc.seo_score,
                brand_score=hc.brand_score,
                overall_score=hc.overall_score,
                selected=hc.selected,
                selection_reason=hc.selection_reason,
            )
            self.session.add(db_hc)

        await self.session.commit()

        # 7. SECTION WRITING (Section 41-44)
        project.status = DraftProjectStatus.WRITING.value
        await self.session.commit()

        rendered_sections: list[DraftSection] = []
        is_native_lang = project.language.lower() in ("hi", "es")

        for sec_bp in blueprint_data.sections:
            sec_facts = allocation_result.allocated_claims.get(sec_bp.section_id, [])
            if is_native_lang:
                sec_draft = MultilingualEngine.adapt_section(
                    section_bp=sec_bp,
                    allocated_facts=sec_facts,
                    language=project.language,
                    topic=research_pkg.topic,
                )
            else:
                sec_draft = SectionWriter.write_section(
                    section_bp=sec_bp,
                    allocated_facts=sec_facts,
                    research_pkg=research_pkg,
                    brand_tone=strategy_data.tone,
                )
            rendered_sections.append(sec_draft)

        # 8. ASSEMBLY (Section 88-91)
        project.status = DraftProjectStatus.ASSEMBLING.value
        await self.session.commit()

        intro_text = DraftAssembler.generate_introduction(
            topic=research_pkg.topic,
            primary_keyword=project.primary_keyword,
            blueprint=blueprint_data,
            research_pkg=research_pkg,
        )
        conclusion_text = DraftAssembler.generate_conclusion(
            topic=research_pkg.topic,
            strategy=strategy_data,
            blueprint=blueprint_data,
            research_pkg=research_pkg,
        )
        tables = DraftAssembler.generate_tables(blueprint_data, research_pkg)
        faqs = DraftAssembler.generate_faqs(blueprint_data, research_pkg)

        article_obj, full_markdown = DraftAssembler.assemble_article(
            headline=winning_headline,
            introduction=intro_text,
            sections=rendered_sections,
            tables=tables,
            faqs=faqs,
            conclusion=conclusion_text,
        )

        # 9. SEO & BRAND VOICE OPTIMIZATION (Section 50-56, 79-81)
        project.status = DraftProjectStatus.OPTIMIZING.value
        await self.session.commit()

        slug_candidate = SemanticSEOOptimizer.generate_slug(winning_headline, project.primary_keyword)
        meta_title = SemanticSEOOptimizer.generate_meta_title(winning_headline, project.primary_keyword)
        meta_description = SemanticSEOOptimizer.generate_meta_description(research_pkg.topic, project.primary_keyword, blueprint_data.article_promise)
        seo_score = SemanticSEOOptimizer.calculate_seo_content_score(
            title=winning_headline,
            content=full_markdown,
            primary_keyword=project.primary_keyword,
            has_faq=bool(faqs),
            has_table=bool(tables),
        )

        # Brand voice application
        brand_profile = None
        if brand_voice_id:
            bv_stmt = select(BrandVoiceProfile).where(BrandVoiceProfile.id == brand_voice_id)
            bv_res = await self.session.execute(bv_stmt)
            db_bv = bv_res.scalar_one_or_none()
            if db_bv:
                brand_profile = BrandVoiceProfileResponse.from_orm(db_bv)

        brand_applied = False
        if brand_profile:
            full_markdown, brand_applied = BrandVoiceEngine.apply_voice(full_markdown, brand_profile)

        # 10. GROUNDING & QUALITY VERIFICATION (Section 104-118)
        project.status = DraftProjectStatus.CHECKING.value
        await self.session.commit()

        grounding_report = GroundingVerifier.verify_draft(
            content=full_markdown,
            research_pkg=research_pkg,
        )

        quality_scores = DraftQualityScorer.score_draft(
            content=full_markdown,
            title=winning_headline,
            primary_keyword=project.primary_keyword,
            grounding_score=grounding_report.grounding_score,
            seo_content_score=seo_score,
            research_pkg=research_pkg,
            is_high_risk=is_high_risk,
            brand_voice_applied=brand_applied,
        )

        # 11. REVISION LOOP (Section 119-121)
        current_cycle = 1
        while not quality_scores.quality_gate_passed and current_cycle <= RevisionEngine.MAX_REVISION_CYCLES:
            project.status = DraftProjectStatus.REVISING.value
            await self.session.commit()

            rev_plan = RevisionEngine.create_revision_plan(
                quality_scores=quality_scores,
                grounding_report=grounding_report,
                sections=rendered_sections,
                current_cycle=current_cycle,
            )

            if rev_plan.should_abort or not rev_plan.tasks:
                break

            for t_item in rev_plan.tasks:
                target_sec = next((s for s in rendered_sections if s.section_id == t_item.get("section_id")), rendered_sections[0])
                revised_sec = RevisionEngine.apply_revision(target_sec, t_item["instruction"])
                # Replace section
                rendered_sections = [revised_sec if s.section_id == revised_sec.section_id else s for s in rendered_sections]

            # Re-assemble
            article_obj, full_markdown = DraftAssembler.assemble_article(
                headline=winning_headline,
                introduction=intro_text,
                sections=rendered_sections,
                tables=tables,
                faqs=faqs,
                conclusion=conclusion_text,
            )

            # Re-verify
            grounding_report = GroundingVerifier.verify_draft(content=full_markdown, research_pkg=research_pkg)
            quality_scores = DraftQualityScorer.score_draft(
                content=full_markdown,
                title=winning_headline,
                primary_keyword=project.primary_keyword,
                grounding_score=grounding_report.grounding_score,
                seo_content_score=seo_score,
                research_pkg=research_pkg,
                is_high_risk=is_high_risk,
                brand_voice_applied=brand_applied,
            )
            current_cycle += 1

        # 12. INTERNAL LINKING (Section 93-94)
        sec_dicts = [{"section_id": s.section_id, "content": s.content} for s in rendered_sections]
        internal_links = InternalLinkPlanner.identify_candidates(sec_dicts, existing_site_content)
        for il in internal_links:
            db_il = InternalLinkCandidate(
                draft_project_id=project.id,
                source_section_id=il.source_section_id,
                target_content_id=uuid.UUID(il.target_content_id) if il.target_content_id else None,
                target_url=il.target_url,
                recommended_anchor_context=il.recommended_anchor_context,
                relevance_score=il.relevance_score,
                reason=il.reason,
            )
            self.session.add(db_il)

        # 13. PERSIST DRAFT VERSION & SENTENCE GROUNDINGS
        content_hash = hashlib.sha256(full_markdown.encode("utf-8")).hexdigest()
        db_draft_version = DraftVersion(
            draft_project_id=project.id,
            version_number=project.writer_version,
            title=winning_headline,
            slug_candidate=slug_candidate,
            meta_title=meta_title,
            meta_description=meta_description,
            content=full_markdown,
            sections_json=[s.dict() for s in rendered_sections],
            faq_json=[f.dict() for f in faqs],
            tables_json=[t.dict() for t in tables],
            content_hash=content_hash,
            generation_reason="initial_generation" if current_cycle == 1 else "revised_generation",
            grounding_score=quality_scores.grounding,
            quality_score=quality_scores.draft_quality,
        )
        self.session.add(db_draft_version)
        await self.session.flush()

        for s_detail in grounding_report.sentence_details:
            db_sg = SentenceGrounding(
                draft_version_id=db_draft_version.id,
                section_id=s_detail.section_id,
                sentence_index=s_detail.sentence_index,
                sentence_text=s_detail.sentence_text,
                sentence_text_hash=hashlib.sha256(s_detail.sentence_text.encode("utf-8")).hexdigest(),
                claim_ids_json=s_detail.claim_ids,
                grounding_status=s_detail.grounding_status,
                confidence=s_detail.confidence,
            )
            self.session.add(db_sg)

        # 14. ASSEMBLE EDITORIAL DRAFT PACKAGE (Section 146 canonical handoff)
        pkg_data = EditorialDraftPackageData(
            draft_project_id=str(project.id),
            research_package_id=str(project.research_package_id),
            opportunity_id=str(project.opportunity_id),
            content_type=project.content_type,
            primary_keyword=project.primary_keyword,
            primary_intent=project.primary_intent,
            target_audience=project.target_audience or [],
            strategy=strategy_data.dict(),
            headline=winning_headline,
            slug_candidate=slug_candidate,
            meta_title=meta_title,
            meta_description=meta_description,
            article=article_obj,
            claim_usage=[
                {"claim_id": c_id, "section_id": s_id}
                for s_id, facts in allocation_result.allocated_claims.items()
                for c_id in [f.claim_id for f in facts]
            ],
            citation_map=[
                {"claim_id": c_id, "source_ids": s_ids}
                for c_id, s_ids in research_pkg.citation_map.items()
            ],
            internal_link_candidates=[il.dict() for il in internal_links],
            schema_candidates=["Article", "FAQPage"] if faqs else ["Article"],
            social_metadata={
                "og_title": winning_headline,
                "og_description": meta_description,
            },
            quality=quality_scores,
            risk_flags=research_pkg.risk_flags,
            research_followups=[],
            revalidate_after=(datetime.now(UTC)).isoformat(),
            draft_version=project.writer_version,
            generation_metadata={
                "strategy_version": f"v{project.strategy_version}",
                "writer_version": f"v{project.writer_version}",
                "prompt_version": project.prompt_version,
            },
        )

        db_pkg = EditorialDraftPackage(
            draft_project_id=project.id,
            research_package_id=project.research_package_id,
            opportunity_id=project.opportunity_id,
            version=project.writer_version,
            status="ready_for_part6" if quality_scores.quality_gate_passed else "needs_human_review",
            quality_score=quality_scores.draft_quality,
            grounding_score=quality_scores.grounding,
            intent_score=quality_scores.intent_satisfaction,
            package_json=pkg_data.dict(),
        )
        self.session.add(db_pkg)

        # 15. Finalize Project State
        project.draft_quality_score = quality_scores.draft_quality
        project.grounding_score = quality_scores.grounding
        project.readability_score = quality_scores.readability
        project.intent_alignment_score = quality_scores.intent_satisfaction
        project.information_gain_score = quality_scores.information_gain
        project.seo_content_score = quality_scores.seo_content
        project.brand_voice_score = quality_scores.brand_voice
        project.status = DraftProjectStatus.READY_FOR_PART6.value if quality_scores.quality_gate_passed else DraftProjectStatus.NEEDS_HUMAN_REVIEW.value
        project.completed_at = datetime.now(UTC)

        await self.session.commit()
        return pkg_data
