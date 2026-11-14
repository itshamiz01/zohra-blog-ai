"""
Zohra — Master Publication Quality Firewall Pipeline (Part 6).

Full independent verification orchestrator:
1. Version & Package Validation (locks draft to research package version).
2. Content Parsing into indexed segments.
3. Independent Claim Extraction.
4. Claim ↔ Evidence Matching & Entailment.
5. Grounding Recalculation.
6. Citation Existence, Entailment & Coverage.
7. Deterministic Numbers, Dates, and Currencies.
8. Quotations & Required Attribution.
9. Temporal Freshness & Deadlines.
10. Hallucination Detection (Fake Experience, Fake Authority).
11. Originality & N-Gram Overlap Analysis.
12. Search Intent & Latency Audit.
13. Technical & Semantic SEO Audit.
14. Editorial Quality & AI-Slop Audit.
15. Risk & Safety Gate (Medical, Finance, Political Neutrality).
16. Adversarial Review Pass (Prompt injection defense).
17. Quality Score Aggregation & Critical Overrides.
18. Publication Firewall Decision & Packaging.
19. Cryptographic Audit Fingerprint & Signed Token Generation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.audit.adversarial.reviewer import AdversarialReviewer
from app.audit.citations.auditor import CitationValidator
from app.audit.claims.extractor import IndependentClaimExtractor
from app.audit.claims.matcher import ClaimMatcher
from app.audit.decision.engine import AuditDecisionEngine
from app.audit.deterministic.numeric_date import NumericDateValidator
from app.audit.deterministic.quotes_attribution import QuoteAttributionValidator
from app.audit.editorial.quality import EditorialQualityAuditor
from app.audit.grounding.scorer import GroundingScorer
from app.audit.hallucination.detector import HallucinationDetector
from app.audit.intent.auditor import SearchIntentAuditor
from app.audit.originality.auditor import OriginalityAuditor
from app.audit.parser.content_parser import ContentParser
from app.audit.risk.engine import ContentRiskEngine
from app.audit.scoring.aggregator import ScoreAggregator
from app.audit.security.token import AuditTokenManager
from app.audit.seo.auditor import SEOAuditor
from app.audit.temporal.freshness import TemporalFreshnessValidator
from app.schemas.audit import (
    AuditDecision,
    AuditIssueItem,
    ClaimMatchResult,
    FinalAuditPackageData,
    HumanReviewPackage,
    IssueSeverity,
    ResearchReturnPackage,
    RevisionPackage,
)


class AuditPipeline:
    """Master orchestrator for independent editorial audit and quality firewall."""

    def __init__(self) -> None:
        self.parser = ContentParser()
        self.claim_extractor = IndependentClaimExtractor()
        self.claim_matcher = ClaimMatcher()
        self.grounding_scorer = GroundingScorer()
        self.citation_validator = CitationValidator()
        self.numeric_validator = NumericDateValidator()
        self.quote_validator = QuoteAttributionValidator()
        self.temporal_validator = TemporalFreshnessValidator()
        self.hallucination_detector = HallucinationDetector()
        self.originality_auditor = OriginalityAuditor()
        self.intent_auditor = SearchIntentAuditor()
        self.seo_auditor = SEOAuditor()
        self.editorial_auditor = EditorialQualityAuditor()
        self.risk_engine = ContentRiskEngine()
        self.adversarial_reviewer = AdversarialReviewer()
        self.score_aggregator = ScoreAggregator()
        self.decision_engine = AuditDecisionEngine()
        self.token_manager = AuditTokenManager()

    def run_audit(
        self,
        editorial_package_json: dict[str, Any],
        research_package_json: dict[str, Any],
        draft_project_id: str,
        research_package_id: str,
        opportunity_id: str,
        site_id: str,
        draft_version_number: int = 1,
        research_package_version: int = 1,
        existing_site_content: list[dict[str, Any]] | None = None,
        custom_risk_policy: dict[str, Any] | None = None,
        policy_version: str = "policy-v1.0",
        audit_id: str | None = None,
    ) -> tuple[
        FinalAuditPackageData,
        list[AuditIssueItem],
        list[ClaimMatchResult],
        RevisionPackage | None,
        ResearchReturnPackage | None,
        HumanReviewPackage | None,
    ]:
        """Executes full multi-pass independent audit."""
        active_audit_id = audit_id or str(uuid.uuid4())
        all_issues: list[AuditIssueItem] = []
        required_checks: dict[str, str] = {}

        # 1. Version & Package Validation
        package_res_id = str(editorial_package_json.get("research_package_id", ""))
        if package_res_id and package_res_id != str(research_package_id):
            all_issues.append(
                AuditIssueItem(
                    issue_code="RESEARCH_PACKAGE_MISMATCH",
                    issue_category="package_validation",
                    severity=IssueSeverity.CRITICAL,
                    description=f"Draft was built against research package {package_res_id} but audited against {research_package_id}.",
                    recommended_action="Rebase draft against the active research package version.",
                    routing_target="part5_writer",
                )
            )

        # 2. Parse Content
        parsed_content = self.parser.parse(editorial_package_json)
        content_hash = parsed_content.content_hash
        required_checks["parser"] = "PASS"

        # 3. Independent Claim Extraction
        extracted_claims = self.claim_extractor.extract_claims(parsed_content)

        # 4. Claim Matching & Entailment
        claim_matches = self.claim_matcher.match_claims(extracted_claims, research_package_json)
        required_checks["claim_audit"] = "PASS"

        for cm in claim_matches:
            if cm.verification_status == "CONTRADICTED":
                all_issues.append(
                    AuditIssueItem(
                        issue_code="FACT_CONTRADICTED",
                        issue_category="factual",
                        severity=IssueSeverity.CRITICAL,
                        section_id=cm.section_id,
                        sentence_index=cm.sentence_index,
                        description=f"Contradicted claim asserted: '{cm.claim_text[:80]}...'",
                        recommended_action="Remove or clearly state as disputed contradiction.",
                        routing_target="part5_writer",
                    )
                )
            elif cm.verification_status == "UNSUPPORTED" and cm.importance in ("critical", "major"):
                all_issues.append(
                    AuditIssueItem(
                        issue_code="FACT_UNSUPPORTED",
                        issue_category="factual",
                        severity=IssueSeverity.MAJOR if cm.importance == "major" else IssueSeverity.CRITICAL,
                        section_id=cm.section_id,
                        sentence_index=cm.sentence_index,
                        description=f"Unsupported {cm.importance} claim: '{cm.claim_text[:80]}...'",
                        recommended_action="Ground claim in research evidence or delete.",
                        routing_target="part5_writer",
                    )
                )
            elif cm.verification_status == "ATTRIBUTION_MISSING":
                all_issues.append(
                    AuditIssueItem(
                        issue_code="ATTRIBUTION_MISSING",
                        issue_category="attribution",
                        severity=IssueSeverity.MAJOR,
                        section_id=cm.section_id,
                        sentence_index=cm.sentence_index,
                        description=f"Attribution missing for claim: '{cm.claim_text[:80]}...'",
                        recommended_action="Frame with explicit source attribution.",
                        routing_target="part5_writer",
                    )
                )

        # 5. Independent Grounding Score
        grounding_score = self.grounding_scorer.calculate_score(claim_matches)

        # 6. Citation Validation
        citation_results, cite_issues, citation_score = self.citation_validator.validate_citations(
            content=parsed_content,
            claims=extracted_claims,
            research_package_json=research_package_json,
        )
        all_issues.extend(cite_issues)
        required_checks["citation_audit"] = "PASS" if citation_score >= 80.0 else "FAIL"

        # 7. Deterministic Numbers & Dates
        num_issues, num_score = self.numeric_validator.validate(parsed_content, research_package_json)
        all_issues.extend(num_issues)
        required_checks["numeric_audit"] = "PASS" if num_score >= 80.0 else "FAIL"

        # 8. Quotations & Attributions
        quote_issues, quote_score = self.quote_validator.validate(parsed_content, research_package_json)
        all_issues.extend(quote_issues)
        required_checks["quote_audit"] = "PASS" if quote_score >= 80.0 else "FAIL"

        # 9. Temporal Freshness & Revalidation Deadlines
        reval_after = editorial_package_json.get("revalidate_after")
        temp_issues, temporal_score = self.temporal_validator.validate(
            parsed_content, research_package_json, revalidate_after=reval_after
        )
        all_issues.extend(temp_issues)
        required_checks["temporal_audit"] = "PASS" if temporal_score >= 80.0 else "FAIL"

        # 10. Hallucination Detection
        halluc_issues, halluc_score = self.hallucination_detector.detect(parsed_content, research_package_json)
        all_issues.extend(halluc_issues)
        required_checks["hallucination_audit"] = "PASS" if halluc_score >= 80.0 else "FAIL"

        # 11. Originality & N-Gram Overlap
        orig_issues, originality_score, info_gain_score = self.originality_auditor.audit(
            parsed_content, research_package_json, existing_site_content=existing_site_content
        )
        all_issues.extend(orig_issues)
        required_checks["originality_audit"] = "PASS" if originality_score >= 70.0 else "FAIL"

        # 12. Search Intent & Latency
        primary_kw = editorial_package_json.get("primary_keyword", "")
        primary_intent = editorial_package_json.get("primary_intent", "informational")
        intent_issues, intent_score = self.intent_auditor.audit(
            parsed_content, primary_kw, primary_intent, research_package_json
        )
        all_issues.extend(intent_issues)
        required_checks["intent_audit"] = "PASS" if intent_score >= 75.0 else "FAIL"

        # 13. SEO Quality & Stuffing
        seo_issues, seo_score = self.seo_auditor.audit(parsed_content, primary_kw)
        all_issues.extend(seo_issues)
        required_checks["seo_audit"] = "PASS" if seo_score >= 75.0 else "FAIL"

        # 14. Editorial Quality & Structure
        edit_issues, content_quality_score, structure_score = self.editorial_auditor.audit(parsed_content)
        all_issues.extend(edit_issues)
        required_checks["editorial_audit"] = "PASS" if content_quality_score >= 75.0 else "FAIL"

        # 15. Risk Engine & Gates
        opp_topic = research_package_json.get("topic", "")
        risk_level, hr_required, risk_issues, risk_score = self.risk_engine.evaluate_risk(
            parsed_content, opp_topic, configured_policy=custom_risk_policy
        )
        all_issues.extend(risk_issues)
        required_checks["risk_audit"] = "PASS"

        # 16. Adversarial Pass
        adv_issues, adv_score = self.adversarial_reviewer.review(parsed_content, research_package_json)
        all_issues.extend(adv_issues)
        required_checks["adversarial_review"] = "PASS" if adv_score >= 80.0 else "FAIL"

        # 17. Quality Score Aggregation & Critical Overrides
        factual_score = (num_score * 0.4) + (quote_score * 0.3) + (halluc_score * 0.3)
        scores, critical_failures = self.score_aggregator.aggregate(
            factual_score=factual_score,
            grounding_score=grounding_score,
            citation_score=citation_score,
            temporal_score=temporal_score,
            originality_score=originality_score,
            intent_score=intent_score,
            info_gain_score=info_gain_score,
            seo_score=seo_score,
            content_quality_score=content_quality_score,
            structure_score=structure_score,
            brand_score=90.0,
            risk_score=risk_score,
            issues=all_issues,
        )

        # 18. Publication Firewall Decision & Packaging
        decision, dec_reason, rev_pkg, res_pkg, hr_pkg = self.decision_engine.decide(
            scores=scores,
            critical_failures=critical_failures,
            issues=all_issues,
            risk_level=risk_level,
            human_review_required=hr_required,
            required_checks=required_checks,
            draft_project_id=draft_project_id,
            draft_version_number=draft_version_number,
            research_package_id=research_package_id,
        )

        eligible_for_part7 = (decision == AuditDecision.PASS)

        # 19. Generate Audit Fingerprint & Signed Cryptographic Token
        fingerprint = self.token_manager.generate_audit_fingerprint(
            content_hash=content_hash,
            research_package_version=research_package_version,
            policy_version=policy_version,
        )
        now_dt = datetime.now(UTC)
        audit_token = self.token_manager.sign_audit_token(
            audit_id=active_audit_id,
            content_hash=content_hash,
            audit_fingerprint=fingerprint,
            decision=decision.value,
            timestamp=now_dt,
        )

        # Summaries
        claim_summary = {
            "total_material_claims": len(extracted_claims),
            "supported": sum(1 for m in claim_matches if m.verification_status == "SUPPORTED"),
            "partially_supported": sum(1 for m in claim_matches if m.verification_status == "PARTIALLY_SUPPORTED"),
            "unsupported": sum(1 for m in claim_matches if m.verification_status == "UNSUPPORTED"),
            "contradicted": sum(1 for m in claim_matches if m.verification_status == "CONTRADICTED"),
            "attribution_missing": sum(1 for m in claim_matches if m.verification_status == "ATTRIBUTION_MISSING"),
            "scope_mismatch": sum(1 for m in claim_matches if m.verification_status == "SCOPE_MISMATCH"),
        }

        citation_summary = {
            "required": len([c for c in extracted_claims if c.importance == "critical"]),
            "present": len(parsed_content.citations_found),
            "valid": len([cr for cr in citation_results if cr.exists_in_research]),
            "fabricated": len([cr for cr in citation_results if cr.is_fabricated]),
        }

        final_package = FinalAuditPackageData(
            audit_id=active_audit_id,
            draft_project_id=draft_project_id,
            draft_version_number=draft_version_number,
            research_package_id=research_package_id,
            research_package_version=research_package_version,
            scores=scores,
            claim_summary=claim_summary,
            citation_summary=citation_summary,
            issues=all_issues,
            risk={"level": risk_level.value, "human_review_required": hr_required},
            required_checks=required_checks,
            critical_failures=critical_failures,
            decision=decision,
            eligible_for_part7=eligible_for_part7,
            audit_fingerprint=fingerprint,
            content_hash=content_hash,
            audit_token=audit_token,
            policy_version=policy_version,
            completed_at=now_dt.isoformat(),
        )

        return final_package, all_issues, claim_matches, rev_pkg, res_pkg, hr_pkg
