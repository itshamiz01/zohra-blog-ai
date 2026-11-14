# Zohra Trend Scoring & Lifecycle Architecture

## 1. Velocity vs Momentum

- **Velocity** ($0–100$): The instantaneous publication rate across windowed intervals ($15\text{m}, 1\text{h}, 6\text{h}, 24\text{h}$):
  $$\text{Windowed Rate} = 0.40 \cdot N_{15\text{m}} + 0.35 \cdot N_{1\text{h}} + 0.15 \cdot N_{6\text{h}} + 0.10 \cdot N_{24\text{h}}$$
- **Acceleration**:
  $$\text{Acceleration Ratio} = \frac{N_{1\text{h}} + 1}{N_{6\text{h}} / 6 + 1}$$
- **Momentum** ($0–100$): The trajectory and direction of attention. An event with 10 mentions growing $4\times$ has higher momentum than an event with 200 mentions collapsing to zero.

## 2. Preliminary Trend Score Formula

The preliminary Trend Score synthesizes multi-dimensional signals:

| Component | Default Weight | Meaning |
|---|---|---|
| **Velocity** | 25% | Publication speed across recent time windows |
| **Momentum** | 20% | Growth rate and positive acceleration |
| **Source Diversity** | 15% | Spread across independent domains & tiers |
| **Freshness** | 15% | Exponential decay based on category half-life |
| **Authority** | 10% | Average institutional weight of reporting sources |
| **Cross-Platform** | 10% | Presence of community or discussion signals |
| **Confidence** | 5% | Evidence consistency and absence of contradictions |
| **Total** | 100% | Trend Score (0–100) |

## 3. Operational Classifications

| Score Range | Classification | Action |
|---|---|---|
| $0–29$ | Noise | Ignore or quarantine |
| $30–49$ | Weak Signal | Monitor quietly |
| $50–64$ | Monitor | Re-evaluate on next discovery cycle |
| $65–74$ | Emerging | Early notification, eligible for fast-track analysis |
| $75–84$ | Trending | High editorial interest |
| $85–94$ | High Velocity | Breaking priority |
| $95–100$ | Exceptional Signal | Major global occurrence |

## 4. Lifecycle State Machine

```text
[EMERGING] ──(growth)──► [ACTIVE] ──(acceleration)──► [ACCELERATING]
                                                           │
                                                           ▼
[STABLE] ◄──(plateau)── [DECLINING] ◄──(drop)───────── [PEAKING]
   │
   ▼
[DORMANT] ──(30d inactivity)──► [ARCHIVED]

(At any time, spam/fraud can transition to [REJECTED])
```

## 5. Qualification for Part 3

An event qualifies for Content Opportunity Analysis (Part 3) if and only if:
1. `trend_score >= 60.0`
2. `confidence_score >= 60.0`
3. `status != REJECTED`
4. `spam_probability < 0.60`
5. Category is `ENABLED` or `REVIEW_ONLY` (not `DISABLED`)
