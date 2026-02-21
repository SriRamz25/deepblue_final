def compute_final_risk(user_score: int, amount_score: int, receiver_score: int) -> dict:
    """
    Combine user, amount, and receiver risk scores into a final risk score and action.
    Args:
        user_score (int): User relationship risk (0-100)
        amount_score (int): Amount damage risk (0-100)
        receiver_score (int): Receiver ML fraud risk (0-100)
    Returns:
        dict: Final risk result
    """
    # Step 1: Normalize
    u = user_score / 100.0
    a = amount_score / 100.0
    r = receiver_score / 100.0

    # Step 2: Core fraud logic
    suspicion = 0.6 * r + 0.25 * u + 0.15 * a
    damage_multiplier = 0.5 + 0.5 * a
    weighted_score = suspicion * damage_multiplier

    # Impossible-travel / high-risk receiver override:
    # A fraudulent receiver (L3 >= 70) must always surface as RED,
    # regardless of how low the amount is.  The floor is 90 % of the raw
    # receiver score so the gauge still reflects nuance (e.g. 72 vs 95).
    receiver_floor = 0.90 * r if r >= 0.70 else 0.0

    final_score = max(weighted_score, receiver_floor)
    final_score = min(max(final_score, 0), 1)
    risk_percent = int(round(final_score * 100))

    # Step 3: Decision Policy (3-level: GREEN / YELLOW / RED)
    if risk_percent < 30:
        action = "ALLOW"   # GREEN  — pay normally
    elif risk_percent < 65:
        action = "WARN"    # YELLOW — warning shown, can still pay
    else:
        action = "RED"     # RED    — strong warning + option to flag receiver

    # Step 4: Risk level
    if risk_percent < 30:
        risk_level = "LOW"
    elif risk_percent < 65:
        risk_level = "MODERATE"
    else:
        risk_level = "HIGH"

    return {
        "final_risk_score": risk_percent,
        "action": action,
        "risk_level": risk_level,
        "components": {
            "user_risk": user_score,
            "amount_risk": amount_score,
            "receiver_risk": receiver_score
        }
    }
