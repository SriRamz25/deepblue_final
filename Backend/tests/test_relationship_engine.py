import pandas as pd
from app.core.relationship_engine import analyze_user_relationship
from datetime import datetime, timedelta

def make_history(sender, receiver, txns):
    """Create a DataFrame with sender_upi, receiver_upi, amount, timestamp, status."""
    rows = []
    now = datetime.utcnow()
    for i, (days_ago, amount, status) in enumerate(txns):
        rows.append({
            'sender_upi': sender,
            'receiver_upi': receiver,
            'amount': amount,
            'timestamp': (now - timedelta(days=days_ago)),
            'status': status
        })
    return pd.DataFrame(rows)

def test_first_time():
    df = make_history('a@upi', 'b@upi', [])
    result = analyze_user_relationship('a@upi', 'b@upi', df)
    assert result['is_first_time'] is True
    assert result['user_risk_score'] == 70
    assert result['familiarity'] == 'new'
    assert result['transaction_count'] == 0
    assert result['last_transaction_days'] == -1
    assert result['avg_past_amount'] == 0.0

def test_first_time_empty_df():
    """Empty DataFrame should be treated as first-time."""
    df = pd.DataFrame()
    result = analyze_user_relationship('a@upi', 'b@upi', df)
    assert result['is_first_time'] is True
    assert result['user_risk_score'] == 70

def test_rare():
    df = make_history('a@upi', 'b@upi', [(2, 100, 'SUCCESS')])
    result = analyze_user_relationship('a@upi', 'b@upi', df)
    assert result['is_first_time'] is False
    assert result['user_risk_score'] == 45
    assert result['familiarity'] == 'rare'
    assert result['transaction_count'] == 1
    # Allow ±1 day tolerance for datetime precision
    assert abs(result['last_transaction_days'] - 2) <= 1
    assert result['avg_past_amount'] == 100.0

def test_known():
    txns = [(10, 100, 'SUCCESS'), (20, 200, 'SUCCESS'), (30, 300, 'SUCCESS')]
    df = make_history('a@upi', 'b@upi', txns)
    result = analyze_user_relationship('a@upi', 'b@upi', df)
    assert result['familiarity'] == 'known'
    assert result['transaction_count'] == 3
    assert result['user_risk_score'] == 30
    assert abs(result['last_transaction_days'] - 10) <= 1
    assert abs(result['avg_past_amount'] - 200.0) < 1e-6

def test_trusted():
    txns = [(1, 100, 'SUCCESS'), (2, 200, 'SUCCESS'), (3, 300, 'SUCCESS'), (4, 400, 'SUCCESS'), (5, 500, 'SUCCESS')]
    df = make_history('a@upi', 'b@upi', txns)
    result = analyze_user_relationship('a@upi', 'b@upi', df)
    assert result['familiarity'] == 'trusted'
    assert result['transaction_count'] == 5
    assert result['user_risk_score'] == 10
    assert abs(result['last_transaction_days'] - 1) <= 1
    assert abs(result['avg_past_amount'] - 300.0) < 1e-6

def test_long_gap():
    txns = [(100, 100, 'SUCCESS'), (200, 200, 'SUCCESS')]
    df = make_history('a@upi', 'b@upi', txns)
    result = analyze_user_relationship('a@upi', 'b@upi', df)
    assert result['user_risk_score'] == 55
    assert abs(result['last_transaction_days'] - 100) <= 1

def test_ignore_other_status():
    txns = [(1, 100, 'FAILED'), (2, 200, 'SUCCESS')]
    df = make_history('a@upi', 'b@upi', txns)
    result = analyze_user_relationship('a@upi', 'b@upi', df)
    assert result['transaction_count'] == 1
    assert result['avg_past_amount'] == 200.0
    assert result['familiarity'] == 'rare'

def test_ignore_other_pairs():
    txns = [(1, 100, 'SUCCESS'), (2, 200, 'SUCCESS')]
    df = make_history('a@upi', 'b@upi', txns)
    # Add unrelated
    df2 = make_history('a@upi', 'c@upi', [(1, 999, 'SUCCESS')])
    df3 = make_history('x@upi', 'b@upi', [(1, 888, 'SUCCESS')])
    df = pd.concat([df, df2, df3], ignore_index=True)
    result = analyze_user_relationship('a@upi', 'b@upi', df)
    assert result['transaction_count'] == 2
    assert result['familiarity'] == 'known'

if __name__ == "__main__":
    test_first_time()
    test_first_time_empty_df()
    test_rare()
    test_known()
    test_trusted()
    test_long_gap()
    test_ignore_other_status()
    test_ignore_other_pairs()
    print("All tests passed.")
