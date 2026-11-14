"""
Zohra — Part 9 Optimization Policy Engine & Risk Classification.

Implements Sections 6, 7, 8, 59, 60, 61, 62, 160, 161, 162 of Part 9 Master Prompt:
- Risk Classes A (Low), B (Medium), C (High), and D (Forbidden)
- OptimizationPolicyEngine evaluating eligibility, confidence, volume, age, cooldown, budgets
- Protection of high-value pages and new articles
- Global and per-site autonomy gating
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any

from app.core.config import get_settings
from app.db.models.optimization import OptimizationPolicy, RiskClass

# ── Action Classifications ───────────────────────────────────────────

CLASS_A_ACTIONS = {
    "META_DESCRIPTION_REFINE",
    "NON_FACTUAL_TITLE_REFINE",
    "IMAGE_ALT_TEXT_IMPROVE",
    "FORMATTING_IMPROVEMENT",
    "INTERNAL_LINK_ADDITION",
    "FAQ_RESTRUCTURING",
    "MINOR_HEADING_IMPROVE",
    "SCHEMA_REVALIDATE",
}

CLASS_B_ACTIONS = {
    "SUBSTANTIAL_TITLE_CHANGE",
    "SECTION_ADDITION",
    "CONTENT_EXPANSION",
    "CONTENT_PRUNING",
    "KEYWORD_REPOSITIONING",
    "MAJOR_INTERNAL_LINK_RESTRUCTURE",
    "CONSOLIDATION_PROPOSAL",
    "QUERY_EXPANSION_SECTION",
}

CLASS_C_ACTIONS = {
    "MAJOR_FACTUAL_REWRITE",
    "CHANGING_CONCLUSIONS",
    "REMOVING_SUBSTANTIAL_CONTENT",
    "MERGING_ARTICLES",
    "REDIRECT_URL",
    "CANONICAL_CHANGE",
    "DELETE_PAGE",
    "FINANCIAL_MEDICAL_LEGAL_OPTIMIZE",
    "HIGH_RISK_NEWS_CORRECTION",
}

CLASS_D_FORBIDDEN_ACTIONS = {
    "SECURITY_MODIFICATION",
    "CODE_SELF_REWRITE",
    "CREDENTIAL_MODIFICATION",
    "REMOVE_AUDIT_LOGS",
    "CHANGE_SAFETY_THRESHOLDS",
    "DISABLE_FACT_CHECKING",
    "CHANGE_AUTONOMY_CONTROLS",
    "CHANGE_PERMISSION_SYSTEM",
    "PUBLISH_UNSUPPORTED_CLAIMS",
}


@dataclass
class PolicyEvaluationResult:
    """Outcome of policy evaluation for an optimization candidate or action."""

    eligible: bool
    risk_class: RiskClass
    human_approval_required: bool
    experiment_required: bool
    auto_execute_allowed: bool
    cooldown_satisfied: bool = True
    budget_available: bool = True
    high_value_protected: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def is_forbidden(self) -> bool:
        return self.risk_class == RiskClass.CLASS_D


class OptimizationPolicyEngine:
    """Evaluates optimization proposals against safety boundaries and site policies."""

    @classmethod
    def classify_action(cls, action_type: str) -> RiskClass:
        """Determines the RiskClass for a given optimization action type."""
        normalized = action_type.upper().replace("-", "_").strip()

        if normalized in CLASS_D_FORBIDDEN_ACTIONS:
            return RiskClass.CLASS_D
        if normalized in CLASS_C_ACTIONS:
            return RiskClass.CLASS_C
        if normalized in CLASS_B_ACTIONS:
            return RiskClass.CLASS_B
        if normalized in CLASS_A_ACTIONS:
            return RiskClass.CLASS_A

        # Keyword matching heuristics for dynamic candidate types
        if any(term in normalized for term in ["SECURITY", "CODE", "CREDENTIAL", "BYPASS", "DISABLE_VERIF"]):
            return RiskClass.CLASS_D
        if any(term in normalized for term in ["REDIRECT", "MERGE", "CANONICAL", "DELETE", "FACTUAL_REWRITE"]):
            return RiskClass.CLASS_C
        if any(term in normalized for term in ["EXPANSION", "PRUN", "SUBSTANTIAL", "CONSOLIDATION"]):
            return RiskClass.CLASS_B
        if any(term in normalized for term in ["TITLE", "CTR"]):
            return RiskClass.CLASS_A

        return RiskClass.CLASS_B

    @classmethod
    def evaluate_candidate(
        cls,
        candidate_type: str,
        confidence: float,
        evidence: dict[str, Any],
        policy: OptimizationPolicy | None = None,
        article_metadata: dict[str, Any] | None = None,
        monthly_changes_count: int = 0,
        cooldown_until: datetime.datetime | None = None,
    ) -> PolicyEvaluationResult:
        """
        Comprehensive policy check against safety, volume, age, budgets, and autonomy.
        """
        settings = get_settings()
        reasons: list[str] = []
        meta = article_metadata or {}

        # 1. Global Kill Switch Check
        if not getattr(settings, "OPTIMIZATION_ENABLED", True):
            return PolicyEvaluationResult(
                eligible=False,
                risk_class=RiskClass.CLASS_D,
                human_approval_required=True,
                experiment_required=False,
                auto_execute_allowed=False,
                reasons=["Global optimization kill switch (OPTIMIZATION_ENABLED) is active"],
            )

        # 2. Risk Classification & Forbidden Action Gating
        risk_class = cls.classify_action(candidate_type)
        if risk_class == RiskClass.CLASS_D:
            return PolicyEvaluationResult(
                eligible=False,
                risk_class=RiskClass.CLASS_D,
                human_approval_required=True,
                experiment_required=False,
                auto_execute_allowed=False,
                reasons=[f"Action {candidate_type} is Class D (Forbidden Autonomous Action)"],
            )

        # 3. Policy Active Check
        if policy and policy.enabled is False:
            return PolicyEvaluationResult(
                eligible=False,
                risk_class=risk_class,
                human_approval_required=True,
                experiment_required=False,
                auto_execute_allowed=False,
                reasons=["Optimization policy is disabled for this site/type"],
            )

        # Thresholds
        min_conf = policy.minimum_confidence if (policy and policy.minimum_confidence is not None) else 0.70
        min_impr = policy.minimum_impressions if (policy and policy.minimum_impressions is not None) else 500
        min_clicks = policy.minimum_clicks if (policy and policy.minimum_clicks is not None) else 20
        min_age_days = policy.minimum_article_age_days if (policy and policy.minimum_article_age_days is not None) else 14
        max_changes = policy.max_changes_per_article_per_month if (policy and policy.max_changes_per_article_per_month is not None) else 2

        # 4. Confidence Threshold Check
        if confidence < min_conf:
            reasons.append(f"Confidence {confidence:.2f} below required minimum {min_conf:.2f}")

        # 5. Volume Gating
        impressions = evidence.get("impressions", evidence.get("current_impressions", 0))
        clicks = evidence.get("clicks", evidence.get("current_clicks", 0))
        is_factual_correction = meta.get("is_factual_correction", False)

        # Factual corrections bypass search volume gating per Section 164
        if not is_factual_correction:
            if impressions < min_impr:
                reasons.append(f"Impressions ({impressions}) below required minimum {min_impr}")
            if clicks < min_clicks and candidate_type in {"CTR_IMPROVEMENT", "TITLE_CHANGE"}:
                reasons.append(f"Clicks ({clicks}) below required minimum {min_clicks}")

        # 6. New Article Protection (Section 162)
        article_age_days = meta.get("age_days")
        if article_age_days is not None and article_age_days < min_age_days and not is_factual_correction:
            reasons.append(
                f"Article age ({article_age_days}d) below observation threshold ({min_age_days}d). New article protection active."
            )

        # 7. High-Value Page Protection (Sections 160-161)
        is_high_value = (
            meta.get("is_high_value_protected", False)
            or meta.get("monthly_traffic", 0) > 10000
            or meta.get("revenue_rank", 100) <= 5
        )

        # 8. Cooldown Check
        now = datetime.datetime.now(UTC)
        cooldown_satisfied = True
        if cooldown_until:
            # Normalize to UTC
            cd = cooldown_until if cooldown_until.tzinfo else cooldown_until.replace(tzinfo=UTC)
            if cd > now:
                cooldown_satisfied = False
                reasons.append(f"Article is in optimization cooldown until {cd.isoformat()}")

        # 9. Monthly Change Budget Check (Section 59)
        budget_available = True
        if monthly_changes_count >= max_changes:
            budget_available = False
            reasons.append(
                f"Monthly change limit reached ({monthly_changes_count}/{max_changes} changes this month)"
            )

        # Determine Eligibility
        eligible = len(reasons) == 0

        # Approval Requirements (Sections 6, 7, 135)
        # Class C always requires human approval.
        # Class B requires human approval if policy says so or if page is high-value.
        # High value protected pages always require human approval.
        human_approval_required = False
        if risk_class == RiskClass.CLASS_C or is_high_value:
            human_approval_required = True
        elif risk_class == RiskClass.CLASS_B:
            human_approval_required = policy.human_approval_required if policy else True
        else:
            human_approval_required = policy.human_approval_required if policy else False

        # Auto-Execute Eligibility (Section 6, 61, 62)
        global_auto = getattr(settings, "AUTO_OPTIMIZATION_ENABLED", False)
        policy_auto = policy.auto_execute_allowed if policy else False
        auto_execute_allowed = (
            global_auto
            and policy_auto
            and not human_approval_required
            and eligible
            and risk_class in {RiskClass.CLASS_A, RiskClass.CLASS_B}
            and not is_high_value
        )

        experiment_required = policy.experiment_required if policy else (risk_class == RiskClass.CLASS_B)

        return PolicyEvaluationResult(
            eligible=eligible,
            risk_class=risk_class,
            human_approval_required=human_approval_required,
            experiment_required=experiment_required,
            auto_execute_allowed=auto_execute_allowed,
            cooldown_satisfied=cooldown_satisfied,
            budget_available=budget_available,
            high_value_protected=is_high_value,
            reasons=reasons,
        )
