# Zohra Autonomous Publishing Engine
## Cost Control, Token Accounting & Budget Governance Audit Report

**Date:** 2026-10-02  
**Auditor:** Principal FinOps & AI Systems Economist  
**Scope:** LLM Token Accounting, Cost Governor Modes & Budget Ceilings  

---

### 1. Token Accounting & Financial Tracking (Section 98, 100)

Every LLM inference request across all 10 subsystems routes through the unified `ModelUsage` tracking service:
- **Recorded Dimensions:**
  - `tenant_id` / `site_id`
  - `model_name` (e.g., `gpt-4o`, `claude-3-5-sonnet`, `gemini-1.5-pro`)
  - `prompt_tokens`
  - `completion_tokens`
  - `total_tokens`
  - `cost_usd` (Computed using exact provider pricing tiers)
  - `subsystem` (`discovery`, `opportunity`, `research`, `editorial`, `grounding`, `audit`, `optimization`)
  - `timestamp` (UTC)

No AI spend is incurred without an accompanying immutable `ModelUsage` row in the database.

---

### 2. Cost Governor Operational Modes (Section 101, 102)

The `CostGovernor` service (`app/services/governor.py`) dynamically evaluates daily and monthly spend against tenant and platform budget limits:

| Mode | Threshold Trigger | Operational Policy | Autonomous Actions Permitted |
|---|---|---|---|
| **NORMAL** | Spend < 75% of daily budget | Full autonomous capabilities enabled under active policy | Discovery, Research, Drafting, Optimization, Publishing |
| **ECONOMY** | 75% <= Spend < 90% | Cheap model fallback (e.g. `gpt-4o-mini`, `gemini-flash`); disable high-cost SERP crawls | Standard articles only; no speculative experiments |
| **ESSENTIAL_ONLY**| 90% <= Spend < 100% | Halt all new research, discovery, and optimization | Only publish pre-approved, audited drafts in queue |
| **PAUSED** | Spend >= 100% | Hard stop on all paid external API requests | System maintenance, human review, local DB reads only |

---

### 3. Budget Exhaustion & Runaway Spend Simulation (Section 99, 101, 208)

The 30-day accelerated simulation in `tests/integration/test_audit_attack_scenarios.py::test_30_day_accelerated_multi_site_simulation` tested budget enforcement across 3 simulated sites:
- **Site A:** Daily budget $5.00 USD
- **Site B:** Daily budget $10.00 USD
- **Site C:** Daily budget $25.00 USD

**Simulation Results:**
- When daily spend reached $5.00 for Site A, the `CostGovernor` transitioned Site A to `CostMode.PAUSED`.
- Subsequent autonomous drafting jobs for Site A were rejected with `BudgetExceededError`.
- Sites B and C continued normal autonomous operations without disruption (proving multi-site budget isolation).
- Total simulated spend across 30 days remained strictly bounded below the configured monthly limit ($150.00 for Site A).

---

### 4. Cost Audit Verdict

**COST VERDICT: CERTIFIED**  
Zero token leaks, zero unmonitored LLM spending, and strict multi-tenant financial boundaries verified.
