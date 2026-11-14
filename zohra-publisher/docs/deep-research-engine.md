# Deep Research & Evidence Intelligence Engine (Part 4)

## Overview

Part 4 of the Zohra Autonomous Publishing Engine bridges the strategic content opportunity identified in Part 3 with the content strategy and writing in Part 5.

Part 3 answered:
> **"What should we consider creating, from which search angle, and why?"**

Part 4 answers:
> **"What is actually known about this topic, which sources support each important statement, where do sources disagree, what remains unknown, and what evidence can safely be handed to the writer?"**

---

## The Fundamental Principle

> **"SOURCE SAYS X" $\ne$ "X IS ESTABLISHED AS TRUE"**

- A single source making a claim does not equal verified truth.
- `NO EVIDENCE FOUND` $\ne$ `FALSE` (represented as `UNKNOWN` / `not_found`).
- Conflicting evidence between Source A and Source B does NOT permit guessing or choosing randomly.
- **MODEL KNOWLEDGE IS NOT A SOURCE**: An LLM cannot recall facts from its training weights and present them as external citations. Every fact requires explicit source provenance.

---

## End-to-End Pipeline

```
ContentOpportunityPackage (Part 3)
         ↓
  ResearchPlanner & Question Decomposition
         ↓
  Targeted Query Generation
         ↓
  Source Discovery & Suitability Review
         ↓
  Secure Document Acquisition (SSRF, Sanitizer, Circuit Breaker)
         ↓
  Document Versioning & Content Hashing
         ↓
  Atomic Claim Extraction & Canonicalization (Subject, Predicate, Object, Scope)
         ↓
  Evidence Mapping & Support Direction Evaluation
         ↓
  Cross-Source Corroboration Across Independence Groups
         ↓
  Contradiction Detection & Non-False Conflict Resolution
         ↓
  Timeline Construction with Temporal Precision
         ↓
  Knowledge Graph Relationship Extraction
         ↓
  Coverage & Gap Analysis
         ↓
  Research Quality & Confidence Scoring
         ↓
  Immutable FinalResearchPackage Assembly
         ↓
  Part 5 Content Strategy & Writer
```

---

## Research Depth Levels

| Depth | Use Case | Max Queries | Source Target | Primary Req |
|---|---|---|---|---|
| **LIGHT** | Simple, low-risk informational topic | 4 | 2–3 | Optional |
| **STANDARD** | Normal tutorial, comparison, or explainer | 8 | 4–6 | Preferred |
| **DEEP** | Complex tech topic, multi-tier pricing, competition | 14 | 8–12 | Mandatory for specs/pricing |
| **CRITICAL** | High-risk YMYL (medical, legal, financial, allegations) | 20+ | 12+ | Mandatory primary + corroboration |

---

## Safe Claim Boundaries for Writer (Part 5)

The generated `FinalResearchPackage` delivers explicit writer boundaries:
- `safe_claim_ids`: Verified claims with Level 4 or Level 5 corroboration.
- `attribution_required_claim_ids`: Quotes, subjective assessments, or company claims that must be stated with attribution ("Company X states...").
- `do_not_state_as_fact_claim_ids`: Disputed, weakly supported, or uncorroborated claims.
- `time_sensitive_claim_ids`: Fast-decaying facts (pricing, limits, executive roles) flagged for contextual dating.
