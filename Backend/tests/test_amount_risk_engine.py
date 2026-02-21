from app.core.amount_risk_engine import analyze_amount_risk

def test_low():
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 1200, 'max_amount_30d': 2000}
    result = analyze_amount_risk(500, stats)
    assert result['amount_risk_score'] == 20
    assert result['risk_level'] == 'LOW'
    assert not result['exceeds_recent_max']

def test_medium():
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(1500, stats)
    assert result['amount_risk_score'] == 40
    assert result['risk_level'] == 'MEDIUM'
    assert not result['exceeds_recent_max']

def test_high():
    """3.5x with exceeds_max penalty → 70 + 10 = 80"""
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(3500, stats)
    assert result['amount_risk_score'] == 80  # 70 base + 10 penalty
    assert result['risk_level'] == 'HIGH'
    assert result['exceeds_recent_max']

def test_very_high():
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(12000, stats)
    assert result['amount_risk_score'] == 100  # 100 base, capped
    assert result['risk_level'] == 'VERY_HIGH'
    assert result['exceeds_recent_max']

def test_zero_avg():
    stats = {'avg_amount_30d': 0, 'avg_amount_7d': 0, 'max_amount_30d': 0}
    result = analyze_amount_risk(100, stats)
    assert result['amount_risk_score'] == 100  # inf ratio → 100 base + 10 exceeds
    assert result['risk_level'] == 'VERY_HIGH'
    assert result['exceeds_recent_max']

def test_penalty_cap():
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(10000, stats)
    assert result['amount_risk_score'] == 100  # 100 base, capped at 100
    assert result['risk_level'] == 'VERY_HIGH'

def test_edge_1_2x():
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(1200, stats)
    assert result['amount_risk_score'] == 40
    assert result['risk_level'] == 'MEDIUM'

def test_edge_2x():
    """2x ratio, does not exceed max → 55, MEDIUM"""
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(2000, stats)
    assert result['amount_risk_score'] == 55
    assert result['risk_level'] == 'MEDIUM'

def test_edge_3x():
    """3x ratio, exceeds max → 70 + 10 = 80"""
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(3000, stats)
    assert result['amount_risk_score'] == 80  # 70 + 10 penalty
    assert result['risk_level'] == 'HIGH'

def test_edge_5x():
    """5x ratio, exceeds max → 85 + 10 = 95"""
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(5000, stats)
    assert result['amount_risk_score'] == 95  # 85 + 10 penalty
    assert result['risk_level'] == 'VERY_HIGH'

def test_edge_10x():
    stats = {'avg_amount_30d': 1000, 'avg_amount_7d': 900, 'max_amount_30d': 2000}
    result = analyze_amount_risk(10000, stats)
    assert result['amount_risk_score'] == 100
    assert result['risk_level'] == 'VERY_HIGH'

if __name__ == "__main__":
    test_low()
    test_medium()
    test_high()
    test_very_high()
    test_zero_avg()
    test_penalty_cap()
    test_edge_1_2x()
    test_edge_2x()
    test_edge_3x()
    test_edge_5x()
    test_edge_10x()
    print("All tests passed.")
