"""
LAYER 1 — USER RELATIONSHIP ANALYSIS

Measures familiarity between sender and receiver.
Does NOT detect fraud — only measures UNCERTAINTY.

This layer queries the sender_history DataFrame for past
sender → receiver transactions and computes a relationship risk score.
"""

import pandas as pd
from datetime import datetime
from typing import Optional


def analyze_user_relationship(
    sender_upi: str,
    receiver_upi: str,
    history_df: pd.DataFrame,
    now: Optional[datetime] = None,
) -> dict:
    """
    Analyze the relationship between sender and receiver.

    Args:
        sender_upi: Sender's UPI ID
        receiver_upi: Receiver's UPI ID
        history_df: DataFrame with columns: sender_upi, receiver_upi, amount, timestamp, status
        now: Reference time (defaults to most recent txn or utcnow)

    Returns:
        dict: {
            "user_risk_score": int (0-100),
            "familiarity": str,
            "is_first_time": bool,
            "last_transaction_days": int,
            "transaction_count": int,
            "avg_past_amount": float
        }
    """
    if history_df is None or history_df.empty:
        return _first_time_result()

    # Filter for this sender → receiver pair, only SUCCESSFUL transactions
    mask = (
        (history_df['sender_upi'] == sender_upi)
        & (history_df['receiver_upi'] == receiver_upi)
        & (history_df['status'].str.upper().isin(['SUCCESS', 'COMPLETED']))
    )
    pair_txns = history_df[mask].copy()

    # ── Compute features ─────────────────────
    transaction_count = len(pair_txns)
    is_first_time = transaction_count == 0

    if is_first_time:
        return _first_time_result()

    # Parse timestamps if needed
    if not pd.api.types.is_datetime64_any_dtype(pair_txns['timestamp']):
        pair_txns['timestamp'] = pd.to_datetime(pair_txns['timestamp'])

    # Last transaction days
    if now is None:
        now = datetime.utcnow()
    last_txn_time = pair_txns['timestamp'].max()
    last_transaction_days = (now - last_txn_time).days

    # Average past amount
    avg_past_amount = pair_txns['amount'].mean()

    # ── Familiarity level ────────────────────
    if transaction_count >= 5:
        familiarity = "trusted"
    elif transaction_count >= 2:
        familiarity = "known"
    elif transaction_count == 1:
        familiarity = "rare"
    else:
        familiarity = "new"

    # ── Scoring Logic ────────────────────────
    # User's exact specification:
    if is_first_time:
        score = 50
    elif last_transaction_days > 90:
        score = 30
    elif transaction_count == 1:
        score = 10
    elif transaction_count <= 4:
        score = 5
    else:
        score = 0

    return {
        "user_risk_score": score,
        "familiarity": familiarity,
        "is_first_time": False,
        "last_transaction_days": last_transaction_days,
        "transaction_count": transaction_count,
        "avg_past_amount": round(float(avg_past_amount), 2),
    }


def _first_time_result() -> dict:
    """Default result for first-time sender → receiver."""
    return {
        "user_risk_score": 50,
        "familiarity": "new",
        "is_first_time": True,
        "last_transaction_days": -1,
        "transaction_count": 0,
        "avg_past_amount": 0.0,
    }
