"""
Zohra — Publication Firewall Decision Engine (Part 6).

Evaluates audit results and yields exactly one controlled outcome:
- PASS: All thresholds satisfied, zero critical failures, eligible for Part 7.
- REVISE: Repairable prose, formatting, SEO, or citation placement issues -> Return to Part 5.
- MORE_RESEARCH: Missing essential evidence, expired research deadline -> Return to Part 4.
- HUMAN_REVIEW: Policy-mandated human gate, high-risk topics, prompt injection attempts.
- REJECT: Fundamental unsuitability, severe defamation, unsalvageable duplicate.

Generates surgical RevisionPackage, ResearchReturnPackage, or HumanReviewPackage.
"""

from __future__ import annotations

from typing import Any

from app.schemas.audit import (
    AuditDecision,
    AuditIssueItem,
    AuditQualityScores,
    HumanReviewPackage,
    IssueSeverity,
    ResearchReturnPackage,
    RevisionPackage,
    RiskLevel,
)


class AuditDecisionEngine:
    """Decides publication outcome and packages routing payloads."""

    def decide(
        self,
        scores: AuditQualityScores,
        critical_failures: list[str],
        issues: list[AuditIssueItem],
        risk_level: RiskLevel,
        human_review_required: bool,
        required_checks: dict[str, str],
        draft_project_id: str,
        draft_version_number: int,
        research_package_id: str,
        custom_thresholds: dict[str, float] | None = None,
    ) -> tuple[AuditDecision, dict[str, Any], RevisionPackage | None, ResearchReturnPackage | None, HumanReviewPackage | None]:
        """Calculates final controlled decision and constructs appropriate routing package."""
        thresholds = {
            "overall_quality": 85.0,
            "factual_integrity": 90.0,
            "grounding": 85.0,
            "citation_quality": 85.0,
            "intent_satisfaction": 80.0,
            "temporal_integrity": 85.0,
        }
        if custom_thresholds:
            thresholds.update(custom_thresholds)

        # 1. Critical Failures / Prompt Injections / Unsalvageable Rejections
        if critical_failures:
            # If high risk or prompt injection, route to human review or reject
            if any("PROMPT_INJECTION" in cf or "POLITICAL_ADVOCACY" in cf or "UNSUPPORTED_MEDICAL" in cf for cf in critical_failures):
                decision = AuditDecision.HUMAN_REVIEW
                reason = {"code": "CRITICAL_RISK_OVERRIDE", "failures": critical_failures}
            elif any("SITE_TOPIC_DUPLICATION" in cf for cf in critical_failures):
                decision = AuditDecision.REJECT
                reason = {"code": "DUPLICATE_TOPIC_REJECTION", "failures": critical_failures}
            else:
                decision = AuditDecision.REVISE
                reason = {"code": "CRITICAL_FAIL_OVERRIDE", "failures": critical_failures}

            rev_pkg, res_pkg, hr_pkg = self._build_packages(decision, issues, draft_project_id, draft_version_number, research_package_id, risk_level)
            return decision, reason, rev_pkg, res_pkg, hr_pkg

        # 2. Any required check error or failure blocks PASS
        incomplete_checks = [k for k, v in required_checks.items() if v in ("ERROR", "FAIL", "PENDING")]
        if incomplete_checks:
            # If research specifically is needed
            if "temporal" in incomplete_checks or any(i.routing_target == "part4_research" for i in issues):
                decision = AuditDecision.MORE_RESEARCH
            else:
                decision = AuditDecision.REVISE
            reason = {"code": "INCOMPLETE_REQUIRED_CHECKS", "checks": incomplete_checks}
            rev_pkg, res_pkg, hr_pkg = self._build_packages(decision, issues, draft_project_id, draft_version_number, research_package_id, risk_level)
            return decision, reason, rev_pkg, res_pkg, hr_pkg

        # 3. Policy-mandated Human Review
        if human_review_required or risk_level == RiskLevel.CRITICAL:
            decision = AuditDecision.HUMAN_REVIEW
            reason = {"code": "HIGH_RISK_POLICY_MANDATE", "risk_level": risk_level.value}
            rev_pkg, res_pkg, hr_pkg = self._build_packages(decision, issues, draft_project_id, draft_version_number, research_package_id, risk_level)
            return decision, reason, rev_pkg, res_pkg, hr_pkg

        # 4. Check if Research is missing or expired
        research_issues = [i for i in issues if i.routing_target == "part4_research"]
        if research_issues:
            decision = AuditDecision.MORE_RESEARCH
            reason = {"code": "MISSING_OR_STALE_RESEARCH", "issues": [i.issue_code for i in research_issues]}
            rev_pkg, res_pkg, hr_pkg = self._build_packages(decision, issues, draft_project_id, draft_version_number, research_package_id, risk_level)
            return decision, reason, rev_pkg, res_pkg, hr_pkg

        # 5. Check Score Thresholds
        threshold_failures: list[str] = []
        if scores.overall_score < thresholds["overall_quality"]:
            threshold_failures.append(f"overall_score ({scores.overall_score}) < {thresholds['overall_quality']}")
        if scores.factual_integrity < thresholds["factual_integrity"]:
            threshold_failures.append(f"factual_integrity ({scores.factual_integrity}) < {thresholds['factual_integrity']}")
        if scores.grounding < thresholds["grounding"]:
            threshold_failures.append(f"grounding ({scores.grounding}) < {thresholds['grounding']}")
        if scores.citation_quality < thresholds["citation_quality"]:
            threshold_failures.append(f"citation_quality ({scores.citation_quality}) < {thresholds['citation_quality']}")

        if threshold_failures:
            decision = AuditDecision.REVISE
            reason = {"code": "THRESHOLD_NOT_MET", "failures": threshold_failures}
            rev_pkg, res_pkg, hr_pkg = self._build_packages(decision, issues, draft_project_id, draft_version_number, research_package_id, risk_level)
            return decision, reason, rev_pkg, res_pkg, hr_pkg

        # 6. Check for Open Major Issues
        major_issues = [i for i in issues if i.severity in (IssueSeverity.CRITICAL, IssueSeverity.MAJOR)]
        if major_issues:
            decision = AuditDecision.REVISE
            reason = {"code": "OPEN_MAJOR_ISSUES", "count": len(major_issues)}
            rev_pkg, res_pkg, hr_pkg = self._build_packages(decision, issues, draft_project_id, draft_version_number, research_package_id, risk_level)
            return decision, reason, rev_pkg, res_pkg, hr_pkg

        # 7. PASS: Full satisfaction
        decision = AuditDecision.PASS
        reason = {"code": "ALL_CHECKS_PASSED", "overall_score": scores.overall_score}
        return decision, reason, None, None, None

    def _build_packages(
        self,
        decision: AuditDecision,
        issues: list[AuditIssueItem],
        draft_project_id: str,
        draft_version_number: int,
        research_package_id: str,
        risk_level: RiskLevel,
    ) -> tuple[RevisionPackage | None, ResearchReturnPackage | None, HumanReviewPackage | None]:
        if decision == AuditDecision.REVISE:
            rev_issues = [i for i in issues if i.routing_target == "part5_writer" or i.severity in (IssueSeverity.CRITICAL, IssueSeverity.MAJOR)]
            pkg = RevisionPackage(
                draft_project_id=draft_project_id,
                draft_version_number=draft_version_number,
                target="part5_writer",
                must_preserve_elements=["verified_facts", "approved_headings"],
                issues_to_fix=rev_issues,
                prohibited_changes=["Do not mutate verified citations", "Do not alter numerical data without evidence"],
                revision_guidance="Apply surgical revisions to the flagged sentences and sections.",
            )
            return pkg, None, None

        if decision == AuditDecision.MORE_RESEARCH:
            res_issues = [i for i in issues if i.routing_target == "part4_research"]
            missing_q = [i.description for i in res_issues] or ["Freshness revalidation required."]
            pkg_res = ResearchReturnPackage(
                draft_project_id=draft_project_id,
                research_package_id=research_package_id,
                target="part4_research",
                missing_questions=missing_q,
                affected_claims=[i.issue_code for i in res_issues],
                priority="HIGH",
                freshness_required=True,
                blocked_sections=[i.section_id for i in res_issues if i.section_id],
            )
            return None, pkg_res, None

        if decision == AuditDecision.HUMAN_REVIEW:
            crit_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
            pkg_hr = HumanReviewPackage(
                audit_id="",
                risk_category="policy_gate",
                risk_level=risk_level,
                critical_issues=crit_issues,
                reasons_for_human_review=[i.description for i in crit_issues] or ["Mandatory policy review required for high-risk category."],
                specific_decisions_required=["Confirm whether statements meet regulatory and safety standards."],
            )
            return None, None, pkg_hr

        return None, None, None
