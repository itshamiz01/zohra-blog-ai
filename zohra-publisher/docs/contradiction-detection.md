# Contradiction Detection & False-Contradiction Prevention

## Overview

A fundamental failure mode in automated research systems is mistaking scope differences for factual contradictions.

---

## 1. Preventing False Contradictions

Before flagging a conflict between Claim A and Claim B, `ContradictionDetector` verifies:

### A. Regional Scope Differences
- **Example**: "Model X costs $19/month" (US) vs "Model X costs ₹1,999/month" (India).
- **Rule**: Distinct regions with distinct currencies are regional variants, NOT contradictions.

### B. Temporal Scope & Version Updates
- **Example**: "Free plan allows 100 generations" (September) vs "Free plan allows 200 generations" (October).
- **Rule**: Distinct timestamps indicate a version update. The newer value is classified as current; the older value is retained as historical context (`resolved_by_freshness`).

### C. Tier and Plan Differences
- **Example**: "API costs $20 per million tokens" vs "Pro subscription costs $20/month".
- **Rule**: Distinct predicates or packaging units are separate canonical propositions.

---

## 2. Contradiction Resolution Strategy

When genuine conflicts occur (e.g. conflicting release dates or differing prices in the exact same region and time frame):

1. **Resolution Priority**:
   - Primary Source Authority > Secondary Reporting
   - Freshness (recent documentation > stale reporting)
   - Domain Reliability & Tier
2. **Never By Majority Vote**:
   - If five copied blogs repeat an inaccurate date ("October 8") while the official vendor release announcement states "October 5", the primary source is accepted (`resolved_by_primary_source`).
3. **Escalation to Human Review**:
   - If two Tier 1 sources publish irreconcilable discrepancies with no official record, `resolution_status` is marked `requires_human_review`, and the claim is classified as `DO_NOT_STATE_AS_FACT`.
