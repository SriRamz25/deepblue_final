"""
DATA LOADER — Central CSV Data Access Layer

Loads sender_history.csv and receiver_history.csv into pandas DataFrames
once on first access, then caches in memory for all subsequent calls.
Provides helper functions to compute sender stats and filter history.
"""

import pandas as pd
import threading
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── In-memory cache ──────────────────────────
_sender_df: Optional[pd.DataFrame] = None
_receiver_df: Optional[pd.DataFrame] = None
_lock = threading.Lock()


def load_sender_history() -> pd.DataFrame:
    """Load and cache sender_history.csv as a pandas DataFrame."""
    global _sender_df
    if _sender_df is not None:
        return _sender_df

    with _lock:
        if _sender_df is not None:
            return _sender_df

        path = getattr(settings, "SENDER_CSV_PATH", "demo_data/sender_history.csv")
        if not os.path.exists(path):
            logger.warning(f"Sender CSV not found at {path}")
            _sender_df = pd.DataFrame()
            return _sender_df

        try:
            df = pd.read_csv(path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
            df['status'] = df['status'].str.upper()
            df = df.sort_values('timestamp').reset_index(drop=True)
            _sender_df = df
            logger.info(f"Loaded {len(df)} rows from sender CSV: {path}")
        except Exception as e:
            logger.error(f"Failed to load sender CSV: {e}")
            _sender_df = pd.DataFrame()

        return _sender_df


def load_receiver_history() -> pd.DataFrame:
    """Load and cache receiver_history.csv as a pandas DataFrame."""
    global _receiver_df
    if _receiver_df is not None:
        return _receiver_df

    with _lock:
        if _receiver_df is not None:
            return _receiver_df

        path = getattr(settings, "RECEIVER_CSV_PATH", "demo_data/receiver_history (2).csv")
        if not os.path.exists(path):
            logger.warning(f"Receiver CSV not found at {path}")
            _receiver_df = pd.DataFrame()
            return _receiver_df

        try:
            df = pd.read_csv(path)
            # Combine date + time if separate columns, else use timestamp
            if 'date' in df.columns and 'time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'])
            elif 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
            df['status'] = df['status'].str.upper()
            df = df.sort_values('timestamp').reset_index(drop=True)
            _receiver_df = df
            logger.info(f"Loaded {len(df)} rows from receiver CSV: {path}")
        except Exception as e:
            logger.error(f"Failed to load receiver CSV: {e}")
            _receiver_df = pd.DataFrame()

        return _receiver_df


def get_sender_receiver_history(sender_upi: str, receiver_upi: str) -> pd.DataFrame:
    """
    Filter sender history for a specific sender → receiver pair.
    Returns only rows where sender_upi matches AND receiver_upi matches.
    """
    df = load_sender_history()
    if df.empty:
        return pd.DataFrame()

    mask = (df['sender_upi'] == sender_upi) & (df['receiver_upi'] == receiver_upi)
    return df[mask].copy()


def get_sender_stats(sender_upi: str, now: Optional[datetime] = None) -> Dict:
    """
    Compute transaction statistics for a sender from sender_history.csv.

    Returns:
        dict with avg_amount_30d, avg_amount_7d, max_amount_30d, max_amount_7d,
        txn_count_1h, txn_count_24h, days_since_last_txn, night_txn_ratio,
        frequent_hours
    """
    df = load_sender_history()
    if df.empty:
        return _empty_stats()

    sender_txns = df[df['sender_upi'] == sender_upi].copy()
    if sender_txns.empty:
        return _empty_stats()

    # Use the most recent transaction as reference if now is None
    if now is None:
        now = sender_txns['timestamp'].max()

    # Filter by time windows
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)
    one_hour_ago = now - timedelta(hours=1)

    txns_30d = sender_txns[sender_txns['timestamp'] >= thirty_days_ago]
    txns_7d = sender_txns[sender_txns['timestamp'] >= seven_days_ago]
    txns_24h = sender_txns[sender_txns['timestamp'] >= one_day_ago]
    txns_1h = sender_txns[sender_txns['timestamp'] >= one_hour_ago]

    # All-time stats (used for user-facing messages — more representative)
    all_amounts = sender_txns['amount'].tolist()
    avg_amount_overall = sum(all_amounts) / len(all_amounts) if all_amounts else 0.0
    max_amount_overall = max(all_amounts) if all_amounts else 0.0

    # 30-day stats
    amounts_30d = txns_30d['amount'].tolist()
    avg_amount_30d = sum(amounts_30d) / len(amounts_30d) if amounts_30d else avg_amount_overall
    max_amount_30d = max(amounts_30d) if amounts_30d else max_amount_overall

    # 7-day stats
    amounts_7d = txns_7d['amount'].tolist()
    avg_amount_7d = sum(amounts_7d) / len(amounts_7d) if amounts_7d else avg_amount_30d
    max_amount_7d = max(amounts_7d) if amounts_7d else max_amount_30d

    # Velocity
    txn_count_24h = len(txns_24h)
    txn_count_1h = len(txns_1h)

    # Night transaction ratio (22:00 - 05:00)
    night_mask = txns_30d['timestamp'].dt.hour.apply(lambda h: h >= 22 or h <= 5)
    night_count = night_mask.sum()
    night_txn_ratio = night_count / max(len(txns_30d), 1)

    # Days since last transaction
    last_txn_time = sender_txns['timestamp'].max()
    days_since_last_txn = (now - last_txn_time).days

    # Frequent hours (top 3)
    hours = txns_30d['timestamp'].dt.hour.tolist() if len(txns_30d) > 0 else sender_txns['timestamp'].dt.hour.tolist()
    hour_counts = {}
    for h in hours:
        hour_counts[h] = hour_counts.get(h, 0) + 1
    frequent_hours = set(sorted(hour_counts.keys(), key=lambda h: -hour_counts[h])[:3])

    return {
        "avg_amount_30d": round(avg_amount_30d, 2),
        "avg_amount_7d": round(avg_amount_7d, 2),
        "avg_amount_overall": round(avg_amount_overall, 2),
        "max_amount_30d": round(max_amount_30d, 2),
        "max_amount_7d": round(max_amount_7d, 2),
        "max_amount_overall": round(max_amount_overall, 2),
        "txn_count_24h": txn_count_24h,
        "txn_count_1h": txn_count_1h,
        "night_txn_ratio": round(night_txn_ratio, 4),
        "days_since_last_txn": days_since_last_txn,
        "frequent_hours": frequent_hours,
    }


def get_receiver_profile(receiver_upi: str) -> Dict:
    """
    Build receiver behavioral profile from receiver_history.csv.

    Analyzes:
    - Total transactions received
    - Merchant flag ratio (fraud indicator)
    - Device cloning (multiple device_ids for same receiver)
    - Location mismatches (ip_city != city)
    - Impossible travel (consecutive txns from far-apart cities in short time)
    - Unique senders
    """
    df = load_receiver_history()
    if df.empty:
        return {"exists": False, "total_txns": 0, "fraud_flag_ratio": 0.0,
                "impossible_travel_count": 0, "impossible_travel_events": []}

    recv_txns = df[df['receiver_upi'] == receiver_upi].copy()
    if recv_txns.empty:
        return {"exists": False, "total_txns": 0, "fraud_flag_ratio": 0.0,
                "impossible_travel_count": 0, "impossible_travel_events": []}

    total = len(recv_txns)
    flagged = recv_txns['merchant_flag'].sum() if 'merchant_flag' in recv_txns.columns else 0
    fraud_flag_ratio = flagged / total

    # Device analysis
    unique_devices = recv_txns['device_id'].nunique() if 'device_id' in recv_txns.columns else 1
    unique_senders = recv_txns['sender_upi'].nunique() if 'sender_upi' in recv_txns.columns else 1

    # Location mismatch count (ip_city != city in same row)
    location_mismatches = 0
    if 'ip_city' in recv_txns.columns and 'city' in recv_txns.columns:
        location_mismatches = int(
            (recv_txns['ip_city'].str.lower() != recv_txns['city'].str.lower()).sum()
        )

    # Impossible travel detection
    impossible_travel = detect_impossible_travel(recv_txns)

    # Amount stats for the receiver
    avg_recv_amount = recv_txns['amount'].mean()
    max_recv_amount = recv_txns['amount'].max()

    return {
        "exists": True,
        "total_txns": total,
        "fraud_flag_ratio": round(fraud_flag_ratio, 4),
        "flagged_count": int(flagged),
        "unique_devices": unique_devices,
        "unique_senders": unique_senders,
        "location_mismatches": location_mismatches,
        "impossible_travel_count": impossible_travel["count"],
        "impossible_travel_events": impossible_travel["events"],
        "avg_amount": round(avg_recv_amount, 2),
        "max_amount": round(max_recv_amount, 2),
    }


# ── Indian city coordinates for haversine distance ──
CITY_COORDS = {
    "chennai": (13.0827, 80.2707),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
    "ahmedabad": (23.0225, 72.5714),
    "jaipur": (26.9124, 75.7873),
    "surat": (21.1702, 72.8311),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in km using haversine formula."""
    import math
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def detect_impossible_travel(recv_txns: pd.DataFrame) -> Dict:
    """
    Detect impossible travel in a receiver's transaction history.

    Impossible travel = two consecutive transactions from cities that are
    too far apart to have physically traveled between in the elapsed time.

    Rule: If distance > 200 km and time gap < 2 hours → IMPOSSIBLE TRAVEL

    Args:
        recv_txns: DataFrame of receiver's transactions (must have timestamp + ip_city or city)

    Returns:
        dict: {"count": int, "events": list of {from_city, to_city, time_gap_min, distance_km}}
    """
    events = []

    # Determine city column
    if 'ip_city' not in recv_txns.columns and 'city' not in recv_txns.columns:
        return {"count": 0, "events": []}

    # Sort by timestamp
    sorted_txns = recv_txns.sort_values('timestamp').reset_index(drop=True)

    for i in range(1, len(sorted_txns)):
        prev = sorted_txns.iloc[i - 1]
        curr = sorted_txns.iloc[i]

        prev_city = str(prev.get('ip_city') or prev.get('city', '')).strip().lower()
        curr_city = str(curr.get('ip_city') or curr.get('city', '')).strip().lower()

        if not prev_city or not curr_city or prev_city == curr_city:
            continue

        # Look up coordinates
        prev_coords = CITY_COORDS.get(prev_city)
        curr_coords = CITY_COORDS.get(curr_city)

        if not prev_coords or not curr_coords:
            continue

        # Calculate distance and time gap
        distance_km = _haversine_km(
            prev_coords[0], prev_coords[1],
            curr_coords[0], curr_coords[1]
        )
        time_gap = (curr['timestamp'] - prev['timestamp']).total_seconds()
        time_gap_min = abs(time_gap) / 60.0

        # Rule: > 200 km in < 120 minutes → impossible travel
        if distance_km > 200 and time_gap_min < 120:
            events.append({
                "from_city": prev_city.title(),
                "to_city": curr_city.title(),
                "time_gap_min": round(time_gap_min, 1),
                "distance_km": round(distance_km, 1),
                "timestamp": str(curr['timestamp']),
            })

    return {"count": len(events), "events": events}


def _empty_stats() -> Dict:
    """Return default empty stats for unknown senders."""
    return {
        "avg_amount_30d": 0.0,
        "avg_amount_7d": 0.0,
        "avg_amount_overall": 0.0,
        "max_amount_30d": 0.0,
        "max_amount_7d": 0.0,
        "max_amount_overall": 0.0,
        "txn_count_24h": 0,
        "txn_count_1h": 0,
        "night_txn_ratio": 0.0,
        "days_since_last_txn": 999,
        "frequent_hours": set(),
    }
