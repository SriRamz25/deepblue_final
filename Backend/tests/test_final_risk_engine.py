from app.core.final_risk_engine import compute_final_risk

def test_allow():
    result = compute_final_risk(10, 10, 10)
    assert result['action'] == 'ALLOW'
    assert result['risk_level'] == 'LOW'
    assert result['final_risk_score'] <= 25

def test_warn():
    """Mid-range scores should produce WARN."""
    result = compute_final_risk(50, 50, 50)
    # suspicion = 0.6*0.5 + 0.25*0.5 + 0.15*0.5 = 0.5
    # damage_multiplier = 0.5 + 0.5*0.5 = 0.75
    # final = 0.5 * 0.75 = 0.375 → 38%
    assert result['action'] == 'WARN'
    assert result['risk_level'] == 'MODERATE'

def test_otp():
    """Higher scores should produce OTP."""
    result = compute_final_risk(70, 70, 70)
    assert result['action'] == 'OTP'
    assert result['risk_level'] == 'HIGH'

def test_block():
    result = compute_final_risk(90, 90, 90)
    assert result['action'] == 'BLOCK'
    assert result['risk_level'] == 'CRITICAL'
    assert result['final_risk_score'] >= 71

def test_receiver_dominates():
    """High receiver risk should dominate."""
    result = compute_final_risk(10, 50, 100)
    # suspicion = 0.6*1 + 0.25*0.1 + 0.15*0.5 = 0.725
    # damage = 0.5 + 0.5*0.5 = 0.75
    # final = 0.725 * 0.75 = 0.544 → 54% → OTP
    assert result['final_risk_score'] >= 45

def test_amount_damage_matters():
    """Higher amount should amplify the final score."""
    result1 = compute_final_risk(10, 10, 60)
    result2 = compute_final_risk(10, 100, 60)
    assert result2['final_risk_score'] > result1['final_risk_score']

def test_all_zero():
    """All zero scores should produce ALLOW."""
    result = compute_final_risk(0, 0, 0)
    assert result['action'] == 'ALLOW'
    assert result['final_risk_score'] == 0

def test_all_max():
    """All max scores should produce BLOCK."""
    result = compute_final_risk(100, 100, 100)
    assert result['action'] == 'BLOCK'
    assert result['final_risk_score'] == 100

if __name__ == "__main__":
    test_allow()
    test_warn()
    test_otp()
    test_block()
    test_receiver_dominates()
    test_amount_damage_matters()
    test_all_zero()
    test_all_max()
    print("All tests passed.")
