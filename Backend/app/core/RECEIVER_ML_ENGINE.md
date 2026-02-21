# Receiver Behavior ML Analysis Engine

This module provides a function to analyze the behavioral risk of a receiver using a trained CatBoost model, based on engineered features from the current transaction and sender context.

## Function

```
analyze_receiver_risk(txn_data: dict, context: dict, model) -> dict
```

- **Purpose:**
  - Produces a fraud probability score (0–1) for the receiver using behavioral features and a trained ML model.
  - Does NOT use relationship familiarity or amount risk.
  - Does NOT block/allow; only scores risk.

- **Inputs:**
  - `txn_data`: dict with keys: `amount`, `receiver`, `timestamp` (ISO string or datetime)
  - `context`: dict with sender stats:
    - `avg_amount_7d`, `avg_amount_30d`, `max_amount_7d`, `txn_count_1h`, `txn_count_24h`, `night_txn_ratio`, `days_since_last_txn`, `location_mismatch`, `frequent_hours`
  - `model`: trained CatBoost model with `predict_proba([features])`

- **Features Engineered:**
  - `amount_deviation = (amount - avg_amount_30d) / (avg_amount_30d + 1)`
  - `velocity_ratio = txn_count_1h / (txn_count_24h + 1)`
  - `is_night = 1 if hour in 22–5 else 0`
  - `unusual_hour = 1 if hour not in frequent_hours else 0`
  - `exceeds_recent_max = amount > max_amount_7d`
  - `night_txn_ratio`, `days_since_last_txn`, `location_mismatch` (from context)

- **Feature Vector Order:**
  - `[amount_deviation, velocity_ratio, is_night, unusual_hour, exceeds_recent_max, night_txn_ratio, days_since_last_txn, location_mismatch]`

- **Outputs:**
  - Dictionary with:
    - `receiver_risk_score`: int (0–100)
    - `fraud_probability`: float (0–1)
    - `risk_level`: str ("LOW", "GUARDED", "SUSPICIOUS", "HIGH_RISK")
    - `features_used`: dict

- **Risk Level Mapping:**
  - 0–25: LOW
  - 26–50: GUARDED
  - 51–75: SUSPICIOUS
  - 76–100: HIGH_RISK

- **Constraints:**
  - No user familiarity, no amount risk, no rules, no blocking/allowing.
  - Only receiver behavior via ML.

## Example

```python
from app.core.receiver_ml_engine import analyze_receiver_risk
# model = ... (load CatBoost model)
txn = {'amount': 1000, 'receiver': 'r@upi', 'timestamp': '2026-02-19T10:00:00'}
ctx = {'avg_amount_30d': 100, 'avg_amount_7d': 100, 'max_amount_7d': 200, 'txn_count_1h': 1, 'txn_count_24h': 2, 'night_txn_ratio': 0.1, 'days_since_last_txn': 3, 'location_mismatch': 0, 'frequent_hours': {10}}
result = analyze_receiver_risk(txn, ctx, model)
print(result)
```

## Tests
See `tests/test_receiver_ml_engine.py` for unit tests.
