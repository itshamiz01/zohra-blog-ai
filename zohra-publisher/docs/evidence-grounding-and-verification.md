# Evidence Grounding, Claim Boundaries & Anti-Hallucination
## Zohra Editorial Intelligence System

### 1. Grounding Invariants
1. **Model Memory Isolation**: An LLM cannot generate factual statements from ungrounded parametric memory.
2. **Prohibited Claims Barrier**: Claims with `writer_policy = "do_not_state_as_fact"` (disputed claims, unverified assertions, contradiction casualties) are strictly blocked by `ClaimAllocator`. If any text matches prohibited claims in prose, `GroundingVerifier` immediately flags a grounding violation.
3. **Mandatory Attribution**: Facts marked `attribution_required = True` (company self-reports, single uncorroborated sources) must include explicit attribution keywords (`"According to official documentation"`, `"The company states"`).
4. **Numeric and Scope Exactness**: Numbers, currencies, and dates in generated articles are checked against `important_numbers` and verified claim attributes. Any undeclared statistics trigger numeric mismatch penalties.
5. **No Fake Hands-on Reviews (Section 14)**: The system automatically scans for unauthorized first-hand claims (`"We tested Model X for 3 weeks"`, `"In our lab tests"`) and sanitizes them into evidence-based framing (`"Based on documented specifications and independent reports"`).

---

### 2. Sentence-Level Grounding Map
Every material sentence generated in a draft is mapped into `sentence_grounding`:
- `sentence_index`: Sequence in section.
- `sentence_text`: Exact statement.
- `sentence_text_hash`: Cryptographic signature.
- `claim_ids_json`: Supporting claim UUIDs.
- `grounding_status`: `grounded`, `partially_grounded`, `ungrounded`, `non_factual`, `attribution_required`.
- `confidence`: Grounding certainty score.
