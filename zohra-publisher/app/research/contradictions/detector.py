"""
Zohra — Contradiction Detector & Resolution Engine.

Detects factual conflicts between claims while strictly avoiding false contradictions
caused by regional differences, currency scopes, plan tiers, or temporal version updates.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.schemas.research import ContradictionResolutionStatus


class DetectedContradiction:
    def __init__(
        self,
        claim_a_id: str,
        claim_b_id: str,
        contradiction_type: str,
        severity: str,
        description: str,
        resolution_status: ContradictionResolutionStatus,
        resolution_reason: str,
        preferred_claim_id: str | None = None,
        confidence_score: float = 85.0,
    ):
        self.claim_a_id = claim_a_id
        self.claim_b_id = claim_b_id
        self.contradiction_type = contradiction_type
        self.severity = severity
        self.description = description
        self.resolution_status = resolution_status
        self.resolution_reason = resolution_reason
        self.preferred_claim_id = preferred_claim_id
        self.confidence_score = confidence_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_a_id": self.claim_a_id,
            "claim_b_id": self.claim_b_id,
            "contradiction_type": self.contradiction_type,
            "severity": self.severity,
            "description": self.description,
            "resolution_status": self.resolution_status.value,
            "resolution_reason": self.resolution_reason,
            "preferred_claim_id": self.preferred_claim_id,
            "confidence_score": self.confidence_score,
        }


class ContradictionDetector:
    """Detects and resolves factual contradictions without mistaking scope for conflict."""

    @classmethod
    def detect_contradictions(
        cls,
        claims: Sequence[dict[str, Any]],
    ) -> list[DetectedContradiction]:
        contradictions: list[DetectedContradiction] = []
        n = len(claims)

        for i in range(n):
            c_a = claims[i]
            id_a = str(c_a.get("id", f"claim_{i}"))
            subj_a = (c_a.get("subject") or "").lower().strip()
            pred_a = (c_a.get("predicate") or "").lower().strip()
            val_a = c_a.get("numeric_value")
            curr_a = (c_a.get("currency") or "").upper().strip()
            reg_a = (c_a.get("region") or "").lower().strip()
            time_a = (c_a.get("temporal_scope") or "").lower().strip()
            is_prim_a = bool(c_a.get("has_primary_source", False))
            date_a = c_a.get("effective_date")

            for j in range(i + 1, n):
                c_b = claims[j]
                id_b = str(c_b.get("id", f"claim_{j}"))
                subj_b = (c_b.get("subject") or "").lower().strip()
                pred_b = (c_b.get("predicate") or "").lower().strip()
                val_b = c_b.get("numeric_value")
                curr_b = (c_b.get("currency") or "").upper().strip()
                reg_b = (c_b.get("region") or "").lower().strip()
                time_b = (c_b.get("temporal_scope") or "").lower().strip()
                is_prim_b = bool(c_b.get("has_primary_source", False))
                date_b = c_b.get("effective_date")

                # Only compare claims about the same subject and predicate
                if not (subj_a and subj_b and (subj_a in subj_b or subj_b in subj_a)):
                    continue
                if pred_a != pred_b or not pred_a:
                    continue

                # 1. Scope checks: Region
                # India price vs US price is a regional scope difference, NOT a contradiction
                if reg_a and reg_b and reg_a != reg_b:
                    continue
                if curr_a and curr_b and curr_a != curr_b:
                    continue

                # 2. Scope checks: Version / Time (Historical vs Current)
                # September limit vs October limit is a version update, NOT a contradiction
                if time_a and time_b and time_a != time_b and date_a and date_b:
                    newer_id = id_b if date_b > date_a else id_a
                    contradictions.append(
                        DetectedContradiction(
                            claim_a_id=id_a,
                            claim_b_id=id_b,
                            contradiction_type="temporal_update",
                            severity="minor",
                            description=f"Temporal change from {time_a} to {time_b} for {pred_a}",
                            resolution_status=ContradictionResolutionStatus.RESOLVED_BY_FRESHNESS,
                            resolution_reason=f"Resolved by temporal freshness; newer value applies to {max(time_a, time_b)}",
                            preferred_claim_id=newer_id,
                            confidence_score=92.0,
                        )
                    )
                    continue

                # 3. Numeric Mismatch
                if val_a is not None and val_b is not None and abs(val_a - val_b) > 0.01:
                    # Conflict exists
                    # Resolve by primary source if one is primary and other is secondary
                    if is_prim_a and not is_prim_b:
                        res_status = ContradictionResolutionStatus.RESOLVED_BY_PRIMARY_SOURCE
                        res_reason = "Resolved in favor of Claim A: verified by primary source documentation."
                        pref_id = id_a
                    elif is_prim_b and not is_prim_a:
                        res_status = ContradictionResolutionStatus.RESOLVED_BY_PRIMARY_SOURCE
                        res_reason = "Resolved in favor of Claim B: verified by primary source documentation."
                        pref_id = id_b
                    elif date_a and date_b and date_a != date_b:
                        res_status = ContradictionResolutionStatus.RESOLVED_BY_FRESHNESS
                        pref_id = id_b if date_b > date_a else id_a
                        res_reason = f"Resolved in favor of fresher evidence ({pref_id})."
                    else:
                        res_status = ContradictionResolutionStatus.REQUIRES_HUMAN_REVIEW
                        res_reason = f"Conflicting numeric values ({val_a} vs {val_b}) across secondary sources with no official resolution."
                        pref_id = None

                    contradictions.append(
                        DetectedContradiction(
                            claim_a_id=id_a,
                            claim_b_id=id_b,
                            contradiction_type="numeric_mismatch",
                            severity="critical" if pred_a == "pricing" else "major",
                            description=f"Discrepancy in {pred_a}: {val_a} vs {val_b}",
                            resolution_status=res_status,
                            resolution_reason=res_reason,
                            preferred_claim_id=pref_id,
                            confidence_score=88.0 if pref_id else 45.0,
                        )
                    )

                # 4. Date mismatch for release/launch events
                elif pred_a in ("release_event", "timeline") and time_a and time_b and time_a != time_b:
                    if is_prim_a and not is_prim_b:
                        res_status = ContradictionResolutionStatus.RESOLVED_BY_PRIMARY_SOURCE
                        pref_id = id_a
                        res_reason = "Official launch date from primary announcement accepted."
                    elif is_prim_b and not is_prim_a:
                        res_status = ContradictionResolutionStatus.RESOLVED_BY_PRIMARY_SOURCE
                        pref_id = id_b
                        res_reason = "Official launch date from primary announcement accepted."
                    else:
                        res_status = ContradictionResolutionStatus.UNRESOLVED
                        pref_id = None
                        res_reason = f"Unresolved release date conflict: {time_a} vs {time_b}."

                    contradictions.append(
                        DetectedContradiction(
                            claim_a_id=id_a,
                            claim_b_id=id_b,
                            contradiction_type="date_mismatch",
                            severity="major",
                            description=f"Conflicting dates for {pred_a}: '{time_a}' vs '{time_b}'",
                            resolution_status=res_status,
                            resolution_reason=res_reason,
                            preferred_claim_id=pref_id,
                            confidence_score=90.0 if pref_id else 50.0,
                        )
                    )

        return contradictions
