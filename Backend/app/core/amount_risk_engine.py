def analyze_amount_risk(amount: float, txn_stats: dict) -> dict:
    """
    Analyze the risk of a transaction amount relative to user spending habits.
    Args:
        amount (float): The transaction amount
        txn_stats (dict): {'avg_amount_30d': float, 'avg_amount_7d': float, 'max_amount_30d': float}
    Returns:
        dict: Amount risk analysis result
    """
    avg30 = txn_stats.get('avg_amount_30d', 0.0) or 0.0
    avg7 = txn_stats.get('avg_amount_7d', 0.0) or 0.0
    max30 = txn_stats.get('max_amount_30d', 0.0) or 0.0
    # Use all-time average for ratio (more representative than 30-day window)
    avg_overall = txn_stats.get('avg_amount_overall', 0.0) or avg30 or 0.0
    max_overall = txn_stats.get('max_amount_overall', 0.0) or max30 or 0.0

    ratio_to_avg30 = amount / avg_overall if avg_overall > 0 else float('inf')
    ratio_to_avg7 = amount / avg7 if avg7 > 0 else float('inf')
    exceeds_recent_max = amount > max_overall

    # Scoring logic — amount is ONE signal in a combined engine.
    # Two paths:
    #   (a) No spending history (new user / first payment): use absolute amount tiers.
    #   (b) Known history: use ratio-to-average tiers.
    # This ensures new users paying very large amounts are flagged properly
    # without blocking every small payment.
    if avg_overall == 0:
        # NEW USER — no baseline; score purely on absolute amount
        if amount >= 75000:
            score = 85
        elif amount >= 40000:
            score = 70
        elif amount >= 20000:
            score = 55
        elif amount >= 10000:
            score = 40
        elif amount >= 5000:
            score = 25
        else:
            score = 10
    else:
        # RETURNING USER — score relative to spending history
        if ratio_to_avg30 >= 20:
            score = 85
        elif ratio_to_avg30 >= 10:
            score = 70
        elif ratio_to_avg30 >= 5:
            score = 55
        elif ratio_to_avg30 >= 3:
            score = 40
        elif ratio_to_avg30 >= 2:
            score = 25
        elif ratio_to_avg30 >= 1.2:
            score = 15
        else:
            score = 5
        if exceeds_recent_max:
            score = min(score + 5, 100)

    # Risk level
    if score <= 15:
        risk_level = "LOW"
    elif score <= 40:
        risk_level = "MEDIUM"
    elif score <= 65:
        risk_level = "HIGH"
    else:
        risk_level = "VERY_HIGH"

    return {
        "amount_risk_score": score,
        "ratio_to_avg30": ratio_to_avg30,
        "ratio_to_avg7": ratio_to_avg7,
        "exceeds_recent_max": exceeds_recent_max,
        "risk_level": risk_level
    }
