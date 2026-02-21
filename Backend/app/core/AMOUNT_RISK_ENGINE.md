# Amount Risk Analysis Engine

This module provides a function to analyze the financial risk of a transaction amount for a user, based on their recent spending history.

## Function

```
analyze_amount_risk(amount: float, txn_stats: dict) -> dict
```

- **Purpose:**
  - Measures how damaging a transaction amount is for the sender (not direct fraud detection).
  - Returns a risk score (0–100) and interpretable features based on user spending.

- **Inputs:**
  - `amount`: float, the transaction amount
  - `txn_stats`: dict with keys:
    - `avg_amount_30d`: float
    - `avg_amount_7d`: float
    - `max_amount_30d`: float

- **Outputs:**
  - Dictionary with:
    - `amount_risk_score`: int (0–100)
    - `ratio_to_avg30`: float
    - `ratio_to_avg7`: float
    - `exceeds_recent_max`: bool
    - `risk_level`: str ("LOW", "MEDIUM", "HIGH", "VERY_HIGH")

- **Scoring Logic:**
  - If ratio_to_avg30 >= 10: 100
  - >= 5: 85
  - >= 3: 70
  - >= 2: 55
  - >= 1.2: 40
  - else: 20
  - If exceeds_recent_max: +10 (clamped to 100)

- **Risk Level Mapping:**
  - 0–30: LOW
  - 31–60: MEDIUM
  - 61–85: HIGH
  - 86–100: VERY_HIGH

- **Constraints:**
  - No ML, no receiver data, no device/location, no user familiarity.
  - Only sender’s spending history is used.

## Example

```python
from app.core.amount_risk_engine import analyze_amount_risk

stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
result = analyze_amount_risk(3500, stats)
print(result)
```

## Tests
See `tests/test_amount_risk_engine.py` for unit tests.
