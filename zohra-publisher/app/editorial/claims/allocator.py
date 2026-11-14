"""
Zohra — Claim Allocator (Part 5).

Manages strict allocation of Part 4 claims into article sections:
enforces safe-claim boundaries, tracks attribution requirements, prohibits disputed/unverified
claims from being stated as facts, and prevents duplicate repetition.
"""

from __future__ import annotations

from app.schemas.editorial import ArticleBlueprintData
from app.schemas.research import FinalResearchPackage, VerifiedFactHandoff


class ClaimAllocationResult:
    def __init__(
        self,
        allocated_claims: dict[str, list[VerifiedFactHandoff]],
        safe_claim_ids: set[str],
        attribution_required_ids: set[str],
        prohibited_claim_ids: set[str],
        unallocated_safe_claims: list[VerifiedFactHandoff],
    ):
        self.allocated_claims = allocated_claims
        self.safe_claim_ids = safe_claim_ids
        self.attribution_required_ids = attribution_required_ids
        self.prohibited_claim_ids = prohibited_claim_ids
        self.unallocated_safe_claims = unallocated_safe_claims


class ClaimAllocator:
    """Allocates and guards claims for section generation."""

    @classmethod
    def allocate_claims(
        cls,
        research_pkg: FinalResearchPackage,
        blueprint: ArticleBlueprintData,
    ) -> ClaimAllocationResult:
        writer_instr = research_pkg.instructions_for_writer
        safe_ids = set(writer_instr.safe_claim_ids)
        attrib_ids = set(writer_instr.attribution_required_claim_ids)
        prohibited_ids = set(writer_instr.do_not_state_as_fact_claim_ids)

        # Index verified facts by claim_id
        fact_by_id: dict[str, VerifiedFactHandoff] = {f.claim_id: f for f in research_pkg.verified_facts}

        allocated: dict[str, list[VerifiedFactHandoff]] = {}
        used_claim_ids: set[str] = set()

        for sec in blueprint.sections:
            sec_facts: list[VerifiedFactHandoff] = []
            for cid in sec.target_claim_ids + sec.supporting_claim_ids:
                if cid in prohibited_ids:
                    # STRICT RULE: Prohibited claims must NOT be allocated as facts
                    continue
                if cid in fact_by_id and cid not in used_claim_ids:
                    sec_facts.append(fact_by_id[cid])
                    used_claim_ids.add(cid)
            allocated[sec.section_id] = sec_facts

        # Check for unallocated safe claims
        unallocated = [f for f in research_pkg.verified_facts if f.claim_id in safe_ids and f.claim_id not in used_claim_ids]

        # If there are unallocated safe claims, append them to the most relevant section (e.g. sec_capabilities or sec_overview)
        fallback_sec = "sec_capabilities" if "sec_capabilities" in allocated else (
            "sec_overview" if "sec_overview" in allocated else (blueprint.sections[0].section_id if blueprint.sections else None)
        )
        if fallback_sec and unallocated:
            allocated[fallback_sec].extend(unallocated)
            for u in unallocated:
                used_claim_ids.add(u.claim_id)
            unallocated = []

        return ClaimAllocationResult(
            allocated_claims=allocated,
            safe_claim_ids=safe_ids,
            attribution_required_ids=attrib_ids,
            prohibited_claim_ids=prohibited_ids,
            unallocated_safe_claims=unallocated,
        )
