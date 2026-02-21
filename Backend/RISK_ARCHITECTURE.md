# 🧠 Sentra Pay — 3-Layer Independent Risk Architecture

## Overview

The risk assessment system is designed as a **3-layer independent architecture** where no single layer can detect fraud alone. Fraud risk emerges from the **convergence of multiple independent signals**.

---

## Architecture Diagram

```
                    ┌──────────────────────┐
                    │    PAYMENT REQUEST    │
                    │  (amount, receiver)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   CONTEXT ENGINE      │
                    │  (Pre-fetch ALL data) │
                    │  • User profile       │
                    │  • Transaction stats  │
                    │  • Receiver profile   │
                    └──┬───────┬────────┬──┘
                       │       │        │
          ┌────────────┘       │        └────────────┐
          │                    │                     │
   ┌──────▼──────┐     ┌──────▼──────┐      ┌──────▼──────┐
   │   LAYER 1   │     │   LAYER 2   │      │   LAYER 3   │
   │ Relationship│     │   Amount    │      │  Receiver   │
   │  Analysis   │     │   Damage    │      │  ML Risk    │
   │             │     │  Analysis   │      │             │
   │ Measures:   │     │ Measures:   │      │ Measures:   │
   │ UNCERTAINTY │     │   IMPACT    │      │ SUSPICION   │
   │ (0-100)     │     │   (0-100)   │      │  (0-100)    │
   └──────┬──────┘     └──────┬──────┘      └──────┬──────┘
          │                    │                     │
          └────────────┐       │        ┌────────────┘
                       │       │        │
                    ┌──▼───────▼────────▼──┐
                    │    FINAL ENGINE       │
                    │  Pure Aggregation     │
                    │  NO DB / NO ML        │
                    │                       │
                    │  → ALLOW / WARN /     │
                    │    OTP / BLOCK        │
                    └──────────────────────┘
```

---

## Layer Details

### Layer 1: User Relationship Analysis
**File:** `app/core/relationship_engine.py`

| Property | Value |
|----------|-------|
| **Purpose** | Measures sender-receiver familiarity & uncertainty |
| **Does NOT** | Detect fraud, analyze amounts, or assess receiver reputation |
| **Inputs** | `transaction_count`, `last_transaction_days`, `avg_past_amount` |
| **Output** | `USER_RELATIONSHIP_RISK` (0-100) |

**Scoring Logic:**
- NEW (0 transactions) → Score 80 (maximum uncertainty)
- RARE (1 transaction) → Score ~30
- KNOWN (2-4 transactions) → Score ~15
- ESTABLISHED (5-9) → Low score
- TRUSTED (10+) → Very low score
- Dormant (>90 days since last) → +20 penalty

---

### Layer 2: Amount Damage Analysis
**File:** `app/core/amount_risk_engine.py`

| Property | Value |
|----------|-------|
| **Purpose** | Measures financial damage potential relative to sender behavior |
| **Does NOT** | Know about receiver, relationships, or fraud patterns |
| **Inputs** | `amount`, `avg_amount_30d`, `avg_amount_7d`, `max_amount_30d` |
| **Output** | `AMOUNT_RISK_SCORE` (0-100) |

**Scoring Logic:**
- ≥10x avg → 100
- ≥5x avg → 85
- ≥3x avg → 70
- ≥2x avg → 55
- ≥1.2x avg → 40
- Below avg → 20
- Exceeds recent max → +10

---

### Layer 3: Receiver Fraud Risk (ML Layer)
**File:** `app/core/receiver_ml_engine.py`

| Property | Value |
|----------|-------|
| **Purpose** | Measures receiver suspiciousness only |
| **Does NOT** | Analyze user behavior, transaction amounts, or familiarity |
| **Inputs** | `receiver_info` dict (is_new, risky_history, good_history, avg_risk_score, reputation_score) |
| **Output** | `RECEIVER_ML_FRAUD_SCORE` (0-100) |

**Scoring Logic:**
- Risky history (blocked/failed) → 75-100
- New receiver → 40
- Neutral → 30
- Good history → 10
- External ML reputation increases score if higher

---

### Final Risk Engine
**File:** `app/core/final_risk_engine.py`

| Property | Value |
|----------|-------|
| **Purpose** | Makes final decision by combining all 3 layer scores |
| **Does NOT** | Query DB, run ML, or compute any features |
| **Inputs** | `user_score`, `amount_score`, `receiver_score` (all 0-100) |
| **Output** | `final_risk_score` (0-100), `action`, `risk_level` |

**Combination Formula:**
```
suspicion = 0.60 × receiver_risk + 0.25 × user_risk + 0.15 × amount_risk
damage_multiplier = 0.5 + 0.5 × amount_risk
final_score = suspicion × damage_multiplier
```

This means:
- Receiver risk has the **highest weight** (60%)
- Amount risk acts as a **multiplier** — a risky receiver sending small amounts won't trigger BLOCK
- Relationship uncertainty adds context but doesn't dominate

**Decision Thresholds:**
| Final Score | Risk Level | Action |
|-------------|-----------|--------|
| < 25 | LOW | ALLOW |
| 25-44 | MODERATE | WARN |
| 45-69 | HIGH | OTP |
| ≥ 70 | CRITICAL | BLOCK |

---

## Strict Boundaries

| Layer | Can Use | Cannot Use |
|-------|---------|------------|
| L1 (Relationship) | Sender-receiver transaction history | Amount data, ML scores, receiver reputation |
| L2 (Amount) | Sender's own spending stats | Receiver data, relationship data, ML |
| L3 (Receiver ML) | Receiver profile & reputation | User relationship, amount patterns |
| Final Engine | All 3 scores (0-100) | Database, ML models, raw features |

---

## Data Flow

1. **Context Engine** (`context_engine.py`) pre-fetches ALL data from PostgreSQL
2. Each layer receives **only its permitted inputs** (structured data, not raw queries)
3. Each layer returns a **score (0-100)** and metadata
4. **Final Engine** receives 3 scores and produces a decision
5. **Orchestrator** (`risk_orchestrator.py`) coordinates the entire flow

---

## Example Scenarios

### Scenario 1: Regular payment to trusted contact
- L1: 0 (TRUSTED, 15+ transactions) 
- L2: 20 (normal amount)
- L3: 10 (good history)
- **Final: ~8% → ALLOW** ✅

### Scenario 2: First-time payment, normal amount, clean receiver
- L1: 80 (NEW)
- L2: 20 (normal amount)
- L3: 40 (new receiver)
- **Final: ~30% → WARN** ⚠️

### Scenario 3: First-time, huge amount, suspicious receiver
- L1: 80 (NEW)
- L2: 95 (10x average)
- L3: 85 (risky history)
- **Final: ~82% → BLOCK** 🔴

### Scenario 4: Known contact, large amount, clean receiver
- L1: 15 (KNOWN, 3 transactions)
- L2: 70 (3x average)
- L3: 10 (good history)
- **Final: ~15% → ALLOW** ✅ (normal large payment to friend)
