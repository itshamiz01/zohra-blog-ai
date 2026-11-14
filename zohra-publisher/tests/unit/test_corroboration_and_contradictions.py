"""
Unit tests for Corroboration Engine, Writer Policies, and Contradiction Detection.
"""

from __future__ import annotations

from app.research.contradictions.detector import ContradictionDetector
from app.research.evidence.corroboration import CorroborationEngine
from app.schemas.research import ClaimStatus, ContradictionResolutionStatus, WriterPolicy


def test_corroboration_requires_independent_groups_for_level_3_and_above():
    # 3 evidence items, but all from the SAME independence group (syndicated wire)
    wire_evidence = [
        {"support_direction": "supports", "independence_group_id": "group_wire_pr", "evidence_strength_score": 0.8},
        {"support_direction": "supports", "independence_group_id": "group_wire_pr", "evidence_strength_score": 0.8},
        {"support_direction": "supports", "independence_group_id": "group_wire_pr", "evidence_strength_score": 0.8},
    ]

    res = CorroborationEngine.evaluate_claim_corroboration(wire_evidence)
    # Only 1 independent voice!
    assert res.independent_sources_count == 1
    # Level 2 (single strong) rather than Level 3+
    assert res.verification_level == 2


def test_corroboration_primary_plus_secondary_reaches_level_4():
    multi_evidence = [
        {
            "support_direction": "supports",
            "independence_group_id": "group_official_docs",
            "is_primary_source": True,
            "evidence_strength_score": 0.95,
        },
        {
            "support_direction": "supports",
            "independence_group_id": "group_independent_review_a",
            "is_primary_source": False,
            "evidence_strength_score": 0.85,
        },
    ]

    res = CorroborationEngine.evaluate_claim_corroboration(multi_evidence)
    assert res.independent_sources_count == 2
    assert res.has_primary_source is True
    assert res.verification_level == 4
    assert res.status == ClaimStatus.STRONGLY_SUPPORTED
    assert res.writer_policy == WriterPolicy.SAFE_TO_STATE


def test_contradiction_detector_avoids_false_contradiction_on_regional_pricing():
    claims = [
        {
            "id": "c_us",
            "subject": "Model X",
            "predicate": "pricing",
            "numeric_value": 19.0,
            "currency": "USD",
            "region": "US",
        },
        {
            "id": "c_in",
            "subject": "Model X",
            "predicate": "pricing",
            "numeric_value": 1999.0,
            "currency": "INR",
            "region": "India",
        },
    ]

    contras = ContradictionDetector.detect_contradictions(claims)
    # Regional scope difference should NOT be flagged as a contradiction!
    assert len(contras) == 0


def test_contradiction_detector_resolves_numeric_conflict_by_primary_source():
    claims = [
        {
            "id": "c_official",
            "subject": "Model X Pro",
            "predicate": "pricing",
            "numeric_value": 20.0,
            "currency": "USD",
            "region": "US",
            "has_primary_source": True,
        },
        {
            "id": "c_secondary",
            "subject": "Model X Pro",
            "predicate": "pricing",
            "numeric_value": 25.0,
            "currency": "USD",
            "region": "US",
            "has_primary_source": False,
        },
    ]

    contras = ContradictionDetector.detect_contradictions(claims)
    assert len(contras) == 1
    assert contras[0].resolution_status == ContradictionResolutionStatus.RESOLVED_BY_PRIMARY_SOURCE
    assert contras[0].preferred_claim_id == "c_official"
