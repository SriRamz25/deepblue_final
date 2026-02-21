# User Relationship Analysis Engine

This module provides a function to analyze the relationship between a sender and receiver in a UPI transaction system, based only on their past transaction history.

## Function

```
analyze_user_relationship(sender_upi: str, receiver_upi: str, history_df) -> dict
```

- **Purpose:**
  - Measures how familiar the sender is with the receiver (not direct fraud detection).
  - Returns a risk score (0–100) and interpretable features based on sender→receiver history.

- **Inputs:**
  - `sender_upi`: UPI ID of the sender
  - `receiver_upi`: UPI ID of the receiver
  - `history_df`: pandas DataFrame with columns: `['sender', 'receiver', 'amount', 'timestamp', 'status']`

- **Outputs:**
  - Dictionary with:
    - `user_risk_score`: int (0–100)
    - `familiarity`: str ("trusted", "known", "rare", "new")
    - `is_first_time`: bool
    - `last_transaction_days`: int (days since last transaction, -1 if never)
    - `transaction_count`: int
    - `avg_past_amount`: float

- **Scoring Logic:**
  - First time: 70
  - Long gap (>90 days): 55
  - Only 1 txn: 45
  - 2–4 txns: 30
  - 5+ txns: 10

- **Constraints:**
  - No ML, no amount anomaly, no device/location, no receiver reputation.
  - Only sender→receiver history is used.

## Example

```python
import pandas as pd
from app.core.relationship_engine import analyze_user_relationship

# Example DataFrame
history = pd.DataFrame([
    {'sender': 'a@upi', 'receiver': 'b@upi', 'amount': 100, 'timestamp': '2025-12-01T10:00:00', 'status': 'COMPLETED'},
    {'sender': 'a@upi', 'receiver': 'b@upi', 'amount': 200, 'timestamp': '2026-01-01T10:00:00', 'status': 'COMPLETED'},
])

result = analyze_user_relationship('a@upi', 'b@upi', history)
print(result)
```

## Tests
See `tests/test_relationship_engine.py` for unit tests.
