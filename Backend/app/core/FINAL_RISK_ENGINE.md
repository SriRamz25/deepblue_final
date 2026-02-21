# Final Risk Engine

This module combines the three independent risk analysis layers to produce a final fraud score and action for a transaction.

## Function

```
compute_final_risk(user_score: int, amount_score: int, receiver_score: int) -> dict
```

- **Purpose:**
  - Combines user relationship risk, amount damage risk, and receiver ML fraud risk (all 0–100) into a final risk score and action.
  - Does NOT call database, run ML, or calculate features. Only combines results.

- **Inputs:**
  - `user_score`: int (0–100)
  - `amount_score`: int (0–100)
  - `receiver_score`: int (0–100)

- **Logic:**
  1. Normalize: u, a, r = user_score/100, amount_score/100, receiver_score/100
  2. Suspicion: `suspicion = 0.6*r + 0.25*u + 0.15*a`
  3. Damage multiplier: `damage_multiplier = 0.5 + 0.5*a`
  4. Final score: `final_score = suspicion * damage_multiplier` (clamped 0–1)
  5. risk_percent = int(final_score * 100)
  6. Action:
     - <25: ALLOW
     - <45: WARN
     - <70: OTP
     - else: BLOCK
  7. Risk level:
     - 0–25: LOW
     - 26–45: MODERATE
     - 46–70: HIGH
     - 71–100: CRITICAL

- **Outputs:**
  - Dictionary with:
    - `final_risk_score`: int (0–100)
    - `action`: str (ALLOW, WARN, OTP, BLOCK)
    - `risk_level`: str (LOW, MODERATE, HIGH, CRITICAL)
    - `components`: dict of input scores

## Example

```python
from app.core.final_risk_engine import compute_final_risk
result = compute_final_risk(30, 40, 80)
print(result)
```

## Tests
See `tests/test_final_risk_engine.py` for unit tests.
