# Zohra Autonomous Publishing Engine
## Part 5: Evidence-Grounded Editorial Generation & Drafting Engine

### 1. Architectural Mission & Philosophy
Part 5 transforms the verified, immutable evidence package from Part 4 into search-intent-aligned, audience-specific, highly readable, and strictly grounded editorial articles.
It adheres strictly to the core anti-hallucination constraint:

$$\mathbf{MODEL\ KNOWLEDGE \neq EVIDENCE}$$

The Writer is not an unconstrained text chatbot; it operates as a controlled editorial renderer operating inside a verified evidence boundary. Every material factual statement (numbers, dates, features, quotes, limitations) must anchor directly to a verified claim ID in the Part 4 Research Package.

```text
PART 4 RESEARCH PACKAGE
        ↓
PACKAGE VALIDATION & QUALITY GATE (Score >= 75 / 90)
        ↓
CONTENT STRATEGIST (Reader problem, search intent, angle, information gain)
        ↓
ARTICLE BLUEPRINT BUILDER (Article promise, sections, table/FAQ plans)
        ↓
CLAIM ALLOCATOR (Safe claims assigned, prohibited claims blocked)
        ↓
HEADLINE ENGINE (Multi-factor scoring, clickbait & superlative penalties)
        ↓
SECTION WRITER (Bounded context per section, format adapters: steps/tables/prose)
        ↓
REVIEW RESTRICTION GUARD (Cleanses unauthorized first-hand testing claims)
        ↓
DRAFT ASSEMBLER (Answer-first intro, grounded conclusion, tables, FAQs)
        ↓
SEMANTIC SEO OPTIMIZER (Natural keyword density, H1/H2/H3 hierarchy, slug, meta)
        ↓
AI SLOP DETECTOR (Penalizes clichés, redundancy, low density)
        ↓
BRAND VOICE ENGINE (Stylistic adaptation with factual invariance invariant)
        ↓
GROUNDING VERIFIER (Sentence-level grounding, numeric consistency, quote checks)
        ↓
DRAFT QUALITY SCORER (Canonical 100-pt formula, quality gate)
        ↓
REVISION ENGINE (Targeted section regeneration, max 3 cycles)
        ↓
EDITORIAL DRAFT PACKAGE (Canonical Part 6 handoff artifact)
```

---

### 2. State Machine Lifecycle
`DraftProject` transitions through strictly enforced lifecycle states:
- `QUEUED`: Enqueued for drafting.
- `STRATEGIZING`: Audience analysis, reader problem definition, information gain plan.
- `BLUEPRINTING`: Article promise, section outlines, claim allocation, citation planning.
- `WRITING`: Bounded section generation and format adaptation.
- `ASSEMBLING`: Introduction, transitions, structured tables, FAQs, conclusion.
- `OPTIMIZING`: Semantic SEO, heading hierarchy, brand voice transformation.
- `CHECKING`: Sentence-level grounding check, numeric verification, quality scoring.
- `REVISING`: Targeted section regeneration for isolated weaknesses.
- `READY_FOR_PART6`: Meets quality gate ($\ge 80$ standard, $\ge 90$ high-risk), immutable package persisted.
- `NEEDS_RESEARCH`: Factual deficiency detected $\rightarrow$ follow-up requested from Part 4.
- `NEEDS_HUMAN_REVIEW`: Disputed assertions or max revision cycles exceeded.
