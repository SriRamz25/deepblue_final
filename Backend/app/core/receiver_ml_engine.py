"""
LAYER 3 — RECEIVER BEHAVIOR ML ANALYSIS

Determines whether the receiver behaves like a fraudster using:
  1. Behavioral features engineered from receiver_history.csv
  2. CatBoost model prediction (if available)
  3. Heuristic fallback when model is unavailable

This layer ONLY evaluates receiver behavior — it does NOT use
relationship familiarity or amount risk.
"""

from typing import Dict, Optional, Set
from datetime import datetime
import logging
import numpy as np

logger = logging.getLogger(__name__)


def analyze_receiver_risk(
    txn_data: dict,
    context: dict,
    model=None,
) -> dict:
    """
    Analyze receiver fraud risk using ML + behavioral features.

    Args:
        txn_data: {amount, receiver, timestamp}
        context: Sender stats — {avg_amount_7d, avg_amount_30d, max_amount_7d,
                 txn_count_1h, txn_count_24h, night_txn_ratio,
                 days_since_last_txn, location_mismatch, frequent_hours,
                 impossible_travel_count}
        model: Trained CatBoost model (optional, falls back to heuristic)

    Returns:
        dict: {receiver_risk_score, fraud_probability, risk_level, features_used}
    """
    # ── Step 1: Engineer ML features ─────────
    features = _engineer_features(txn_data, context)

    # ── Step 2: Predict ──────────────────────
    if model is not None:
        try:
            feature_vector = _build_feature_vector(features)
            proba = model.predict_proba([feature_vector])[0][1]
            fraud_probability = float(min(max(proba, 0.0), 1.0))
        except Exception as e:
            logger.warning(f"ML prediction failed, using heuristic: {e}")
            fraud_probability = _heuristic_score(features)
    else:
        fraud_probability = _heuristic_score(features)

    # ── Step 3: Convert to score (0-100) ─────
    receiver_risk_score = int(fraud_probability * 100)

    # Risk level mapping
    if receiver_risk_score <= 25:
        risk_level = "LOW"
    elif receiver_risk_score <= 50:
        risk_level = "GUARDED"
    elif receiver_risk_score <= 75:
        risk_level = "SUSPICIOUS"
    else:
        risk_level = "HIGH_RISK"

    return {
        "receiver_risk_score": receiver_risk_score,
        "fraud_probability": round(fraud_probability, 4),
        "risk_level": risk_level,
        "features_used": features,
    }


def _engineer_features(txn_data: dict, context: dict) -> dict:
    """
    Engineer behavioral features from transaction data and sender context.
    These features match the training schema.
    """
    amount = float(txn_data.get('amount', 0))
    timestamp_str = txn_data.get('timestamp', '')

    # Parse timestamp
    if isinstance(timestamp_str, str):
        try:
            ts = datetime.fromisoformat(timestamp_str)
        except Exception:
            ts = datetime.utcnow()
    elif isinstance(timestamp_str, datetime):
        ts = timestamp_str
    else:
        ts = datetime.utcnow()

    hour = ts.hour

    # Context values (from sender history CSV via get_sender_stats)
    avg_amount_30d      = float(context.get('avg_amount_30d', 0) or 0)
    avg_amount_7d       = float(context.get('avg_amount_7d', 0) or 0)
    max_amount_7d       = float(context.get('max_amount_7d', 0) or 0)
    txn_count_1h        = int(context.get('txn_count_1h', 0) or 0)
    txn_count_24h       = int(context.get('txn_count_24h', 0) or 0)
    night_txn_ratio     = float(context.get('night_txn_ratio', 0) or 0)
    days_since_last_txn = int(context.get('days_since_last_txn', 0) or 0)
    frequent_hours      = context.get('frequent_hours', set()) or set()

    # Receiver profile context (from receiver_history CSV via get_receiver_profile)
    impossible_travel_count = int(context.get('impossible_travel_count', 0) or 0)
    fraud_flag_ratio        = float(context.get('fraud_flag_ratio', 0.0) or 0.0)
    is_new_receiver         = int(context.get('is_new_receiver', 0) or 0)   # 1 = not in recv CSV
    location_mismatch       = int(context.get('location_mismatch', 0) or 0)  # 1 = ip_city != city
    receiver_type           = int(context.get('receiver_type', 0) or 0)      # 0=personal, 1=merchant

    # ── Engineered features matching model training schema (22 features) ──
    import math
    is_night                = 1 if (hour >= 22 or hour <= 5) else 0
    unusual_hour            = 1 if hour not in frequent_hours else 0
    exceeds_recent_max      = amount > max_amount_7d
    is_round_amount         = 1 if (amount > 0 and amount % 1000 == 0) else 0
    velocity_check          = 1 if txn_count_1h > 2 else 0
    deviation_from_avg      = (amount - avg_amount_30d) / (avg_amount_30d + 1)
    amount_log              = math.log1p(amount)
    hour_sin                = math.sin(2 * math.pi * hour / 24)
    hour_cos                = math.cos(2 * math.pi * hour / 24)
    ratio_30d               = amount / (avg_amount_30d + 1)
    velocity_ratio          = txn_count_1h / (txn_count_24h + 1)

    # risk_profile: 0-3 composite signal (higher = more risky)
    risk_profile = 0
    if fraud_flag_ratio >= 0.5:  risk_profile += 1
    if impossible_travel_count > 0: risk_profile += 1
    if is_new_receiver: risk_profile += 1

    return {
        # Raw values (kept for heuristic fallback)
        "amount":               amount,
        "payment_mode":         0,             # 0 = standard UPI pay
        "receiver_type":        receiver_type,
        "is_new_receiver":      is_new_receiver,
        "avg_amount_7d":        avg_amount_7d,
        "avg_amount_30d":       avg_amount_30d,
        "max_amount_7d":        max_amount_7d,
        "txn_count_1h":         txn_count_1h,
        "txn_count_24h":        txn_count_24h,
        "days_since_last_txn":  days_since_last_txn,
        "night_txn_ratio":      round(night_txn_ratio, 4),
        "location_mismatch":    location_mismatch,
        "is_night":             is_night,
        "is_round_amount":      is_round_amount,
        "velocity_check":       velocity_check,
        "deviation_from_sender_avg": round(deviation_from_avg, 4),
        "exceeds_recent_max":   1 if exceeds_recent_max else 0,
        "amount_log":           round(amount_log, 4),
        "hour_sin":             round(hour_sin, 4),
        "hour_cos":             round(hour_cos, 4),
        "ratio_30d":            round(ratio_30d, 4),
        "risk_profile":         risk_profile,
        # Extra signals kept for heuristic
        "unusual_hour":         unusual_hour,
        "impossible_travel_count": impossible_travel_count,
        "fraud_flag_ratio":     round(fraud_flag_ratio, 4),
    }


def _build_feature_vector(features: dict) -> list:
    """
    Build 22-feature numeric vector in EXACT ORDER matching model training schema.
    Feature names (from model.feature_names_):
    amount, payment_mode, receiver_type, is_new_receiver,
    avg_amount_7d, avg_amount_30d, max_amount_7d,
    txn_count_1h, txn_count_24h, days_since_last_txn, night_txn_ratio,
    location_mismatch, is_night, is_round_amount, velocity_check,
    deviation_from_sender_avg, exceeds_recent_max,
    amount_log, hour_sin, hour_cos, ratio_30d, risk_profile
    """
    return [
        features['amount'],
        features['payment_mode'],
        features['receiver_type'],
        features['is_new_receiver'],
        features['avg_amount_7d'],
        features['avg_amount_30d'],
        features['max_amount_7d'],
        features['txn_count_1h'],
        features['txn_count_24h'],
        features['days_since_last_txn'],
        features['night_txn_ratio'],
        features['location_mismatch'],
        features['is_night'],
        features['is_round_amount'],
        features['velocity_check'],
        features['deviation_from_sender_avg'],
        features['exceeds_recent_max'],
        features['amount_log'],
        features['hour_sin'],
        features['hour_cos'],
        features['ratio_30d'],
        features['risk_profile'],
    ]


def _heuristic_score(features: dict) -> float:
    """
    Fallback heuristic when ML model is not available.
    Produces a fraud probability (0-1) from behavioral signals.
    """
    score = 0.0

    # Amount deviation is a strong signal
    dev = features.get('deviation_from_sender_avg', features.get('amount_deviation', 0))
    if dev >= 10:
        score += 0.40
    elif dev >= 5:
        score += 0.30
    elif dev >= 2:
        score += 0.20
    elif dev >= 1:
        score += 0.10

    # Night transaction
    if features['is_night']:
        score += 0.15

    # Unusual hour
    if features['unusual_hour']:
        score += 0.10

    # Exceeds recent max
    if features['exceeds_recent_max']:
        score += 0.10

    # High velocity
    if features.get('velocity_check', 0) or features.get('velocity_ratio', 0) > 0.5:
        score += 0.10

    # Impossible travel — very strong fraud signal
    it_count = features.get('impossible_travel_count', 0)
    if it_count > 0:
        score += min(it_count * 0.20, 0.40)  # up to +0.40

    # Receiver fraud flag ratio from CSV — direct historical evidence
    ffr = features.get('fraud_flag_ratio', 0.0)
    if ffr >= 0.9:
        score += 0.40   # recv6–recv10: 100% flagged
    elif ffr >= 0.7:
        score += 0.30
    elif ffr >= 0.5:
        score += 0.20   # recv5: 50% flagged
    elif ffr >= 0.3:
        score += 0.10

    return min(score, 1.0)
