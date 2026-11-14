# Draft Quality Scoring & Quality Gates
## Zohra Editorial Intelligence System

### 1. Canonical 100-Point Formula (Section 116)

$$\begin{aligned}
\text{Draft Quality Score} = &\ \text{Intent Satisfaction (20)} \\
&+ \text{Grounding (20)} \\
&+ \text{Information Gain (15)} \\
&+ \text{Clarity (10)} \\
&+ \text{Structure (10)} \\
&+ \text{SEO Quality (10)} \\
&+ \text{Citation Quality (5)} \\
&+ \text{Readability (5)} \\
&+ \text{Brand Voice (5)} \\
&- \text{Penalties (Slop, Stuffing, Repetition)}
\end{aligned}$$

---

### 2. Quality Classifications & Gate Thresholds
- **95 – 100**: `EXCEPTIONAL_DRAFT`
- **85 – 94**: `STRONG_DRAFT`
- **75 – 84**: `PART_6_ELIGIBLE`
- **65 – 74**: `REVISION_REQUIRED`
- **50 – 64**: `MAJOR_REVISION`
- **0 – 49**: `REJECT`

#### Gate Requirements:
- Standard Articles: `draft_quality >= 80`, `grounding >= 90`.
- High-Risk Topics (medical, financial, legal): `draft_quality >= 90`, `grounding >= 95`.
If the draft does not meet the required threshold, `RevisionEngine` plans targeted section regenerations (up to 3 cycles). If issues persist, the project is safely routed to `NEEDS_HUMAN_REVIEW` or `NEEDS_RESEARCH`.
