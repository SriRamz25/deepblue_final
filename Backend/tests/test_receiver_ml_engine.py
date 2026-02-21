import numpy as np
from app.core.receiver_ml_engine import analyze_receiver_risk

class DummyModel:
    """Deterministic model: sigmoid of sum of features."""
    def predict_proba(self, X):
        s = float(np.sum(X[0]))
        p = 1 / (1 + np.exp(-s))
        return [[1-p, p]]

def test_low_heuristic():
    """Low-risk scenario with heuristic (no model)."""
    txn = {'amount': 100, 'receiver': 'r@upi', 'timestamp': '2026-02-19T10:00:00'}
    ctx = {'avg_amount_30d': 100, 'avg_amount_7d': 100, 'max_amount_7d': 200,
           'txn_count_1h': 0, 'txn_count_24h': 0, 'night_txn_ratio': 0,
           'days_since_last_txn': 1, 'location_mismatch': 0, 'frequent_hours': {10}}
    result = analyze_receiver_risk(txn, ctx, None)
    assert 0 <= result['fraud_probability'] <= 1
    assert result['risk_level'] in ('LOW', 'GUARDED')

def test_high_heuristic():
    """High-risk scenario with heuristic (no model)."""
    txn = {'amount': 10000, 'receiver': 'r@upi', 'timestamp': '2026-02-19T23:00:00'}
    ctx = {'avg_amount_30d': 100, 'avg_amount_7d': 100, 'max_amount_7d': 200,
           'txn_count_1h': 10, 'txn_count_24h': 10, 'night_txn_ratio': 0.9,
           'days_since_last_txn': 0, 'location_mismatch': 1, 'frequent_hours': {10}}
    result = analyze_receiver_risk(txn, ctx, None)
    assert result['risk_level'] in {'SUSPICIOUS', 'HIGH_RISK'}
    assert result['receiver_risk_score'] >= 50

def test_with_model():
    """With DummyModel, verify output structure."""
    txn = {'amount': 500, 'receiver': 'r@upi', 'timestamp': '2026-02-19T10:00:00'}
    ctx = {'avg_amount_30d': 500, 'avg_amount_7d': 500, 'max_amount_7d': 600,
           'txn_count_1h': 0, 'txn_count_24h': 1, 'night_txn_ratio': 0,
           'days_since_last_txn': 1, 'location_mismatch': 0, 'frequent_hours': {10}}
    result = analyze_receiver_risk(txn, ctx, DummyModel())
    assert 0 <= result['fraud_probability'] <= 1
    assert 0 <= result['receiver_risk_score'] <= 100
    assert result['risk_level'] in ('LOW', 'GUARDED', 'SUSPICIOUS', 'HIGH_RISK')

def test_night_and_unusual():
    txn = {'amount': 500, 'receiver': 'r@upi', 'timestamp': '2026-02-19T03:00:00'}
    ctx = {'avg_amount_30d': 100, 'avg_amount_7d': 100, 'max_amount_7d': 200,
           'txn_count_1h': 1, 'txn_count_24h': 2, 'night_txn_ratio': 0.5,
           'days_since_last_txn': 2, 'location_mismatch': 0, 'frequent_hours': {10, 11}}
    result = analyze_receiver_risk(txn, ctx, None)
    assert result['features_used']['is_night'] == 1
    assert result['features_used']['unusual_hour'] == 1

def test_exceeds_recent_max():
    txn = {'amount': 300, 'receiver': 'r@upi', 'timestamp': '2026-02-19T12:00:00'}
    ctx = {'avg_amount_30d': 100, 'avg_amount_7d': 100, 'max_amount_7d': 200,
           'txn_count_1h': 0, 'txn_count_24h': 1, 'night_txn_ratio': 0,
           'days_since_last_txn': 1, 'location_mismatch': 0, 'frequent_hours': {12}}
    result = analyze_receiver_risk(txn, ctx, None)
    assert result['features_used']['exceeds_recent_max'] is True

def test_feature_order():
    txn = {'amount': 100, 'receiver': 'r@upi', 'timestamp': '2026-02-19T10:00:00'}
    ctx = {'avg_amount_30d': 100, 'avg_amount_7d': 100, 'max_amount_7d': 200,
           'txn_count_1h': 1, 'txn_count_24h': 2, 'night_txn_ratio': 0.1,
           'days_since_last_txn': 3, 'location_mismatch': 0, 'frequent_hours': {10}}
    result = analyze_receiver_risk(txn, ctx, None)
    feats = result['features_used']
    assert list(feats.keys()) == [
        'amount_deviation', 'velocity_ratio', 'is_night', 'unusual_hour',
        'exceeds_recent_max', 'night_txn_ratio', 'days_since_last_txn',
        'location_mismatch', 'impossible_travel_count'
    ]

if __name__ == "__main__":
    test_low_heuristic()
    test_high_heuristic()
    test_with_model()
    test_night_and_unusual()
    test_exceeds_recent_max()
    test_feature_order()
    print("All tests passed.")
