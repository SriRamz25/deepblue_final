"""
Retrain fraud_model.cbm on the actual demo receiver_history.csv data.
Uses the same 22-feature schema the orchestrator engineers.
"""
import sys, os, math
sys.path.insert(0, '.')
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:sentra_secure_2026@localhost:5433/fraud_detection')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('SECRET_KEY', 'key')

import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from app.core.data_loader import load_sender_history, load_receiver_history, get_sender_stats, get_receiver_profile

print("Loading CSVs...")
sender_df = load_sender_history()
receiver_df = load_receiver_history()

# Build training rows: one row per transaction in receiver_history.csv
# Features: engineered from sender stats + receiver profile
rows = []

for _, txn in receiver_df.iterrows():
    sender_upi   = txn['sender_upi']
    receiver_upi = txn['receiver_upi']
    amount       = float(txn['amount'])
    label        = int(txn['merchant_flag'])   # 1=fraud, 0=legit

    try:
        ts = pd.to_datetime(txn['timestamp'])
        hour = ts.hour
    except Exception:
        hour = 12

    # Sender stats from sender CSV
    stats = get_sender_stats(sender_upi)
    avg30   = stats.get('avg_amount_30d', amount)
    avg7    = stats.get('avg_amount_7d',  amount)
    max7    = stats.get('max_amount_7d',  amount)
    cnt1h   = stats.get('txn_count_1h',   0)
    cnt24h  = stats.get('txn_count_24h',  0)
    night_r = stats.get('night_txn_ratio', 0.0)
    days    = stats.get('days_since_last_txn', 0)
    freq_h  = stats.get('frequent_hours', set())

    # Receiver profile from receiver CSV
    profile  = get_receiver_profile(receiver_upi)
    ffr      = profile.get('fraud_flag_ratio', 0.0)
    itc      = profile.get('impossible_travel_count', 0)
    loc_mis  = 1 if profile.get('location_mismatches', 0) > 0 else 0
    is_new   = 0 if profile.get('exists', False) else 1
    recv_type = 1 if ffr > 0.5 else 0

    # Engineered features (22, same order as model schema)
    is_night      = 1 if (hour >= 22 or hour <= 5) else 0
    is_round      = 1 if (amount > 0 and amount % 1000 == 0) else 0
    vel_check     = 1 if cnt1h > 2 else 0
    dev           = (amount - avg30) / (avg30 + 1)
    exceeds_max   = 1 if amount > max7 else 0
    amt_log       = math.log1p(amount)
    h_sin         = round(math.sin(2 * math.pi * hour / 24), 4)
    h_cos         = round(math.cos(2 * math.pi * hour / 24), 4)
    ratio30       = amount / (avg30 + 1)
    risk_profile  = min((1 if ffr >= 0.5 else 0) + (1 if itc > 0 else 0) + is_new, 3)

    rows.append({
        'amount':                  amount,
        'payment_mode':            0,
        'receiver_type':           recv_type,
        'is_new_receiver':         is_new,
        'avg_amount_7d':           avg7,
        'avg_amount_30d':          avg30,
        'max_amount_7d':           max7,
        'txn_count_1h':            cnt1h,
        'txn_count_24h':           cnt24h,
        'days_since_last_txn':     days,
        'night_txn_ratio':         round(night_r, 4),
        'location_mismatch':       loc_mis,
        'is_night':                is_night,
        'is_round_amount':         is_round,
        'velocity_check':          vel_check,
        'deviation_from_sender_avg': round(dev, 4),
        'exceeds_recent_max':      exceeds_max,
        'amount_log':              round(amt_log, 4),
        'hour_sin':                h_sin,
        'hour_cos':                h_cos,
        'ratio_30d':               round(ratio30, 4),
        'risk_profile':            risk_profile,
        'label':                   label,
    })

df = pd.DataFrame(rows)
print(f"Training set: {len(df)} rows | fraud={df['label'].sum()} ({df['label'].mean()*100:.0f}%)")

feature_cols = [c for c in df.columns if c != 'label']
X = df[feature_cols]
y = df['label']

print("Training CatBoost model...")
model = CatBoostClassifier(
    iterations=300,
    learning_rate=0.05,
    depth=6,
    class_weights=[1, 3],   # fraud is minority class
    random_seed=42,
    verbose=False,
)
model.fit(X, y)

# Validate
from sklearn.metrics import roc_auc_score, classification_report
preds = model.predict(X)
proba = model.predict_proba(X)[:, 1]
try:
    auc = roc_auc_score(y, proba)
    print(f"Train AUC: {auc:.4f}")
except Exception:
    pass
print(classification_report(y, preds, target_names=['legit','fraud']))

# Test calibration on specific receivers
print("Calibration test:")
test_cases = [
    ("recv1@upi",  8000,  "clean (0% flagged)"),
    ("recv5@upi",  8000,  "risky (50% flagged)"),
    ("recv6@upi",  8000,  "fraud (100% flagged)"),
    ("recv13@upi", 8000,  "user4 known, clean"),
    ("recv17@upi", 8000,  "fraud (100% flagged, new)"),
]
import math
user4_stats = get_sender_stats("user4@upi")
for recv, amt, note in test_cases:
    prof = get_receiver_profile(recv)
    ffr = prof.get('fraud_flag_ratio', 0.0)
    itc = prof.get('impossible_travel_count', 0)
    is_new = 0 if prof.get('exists') else 1
    rt = 1 if ffr > 0.5 else 0
    rp = min((1 if ffr>=0.5 else 0)+(1 if itc>0 else 0)+is_new, 3)
    avg30 = user4_stats['avg_amount_30d']; avg7 = user4_stats['avg_amount_7d']
    max7 = user4_stats['max_amount_7d']
    vec = [amt,0,rt,is_new,avg7,avg30,max7,0,0,0,0.1,
           1 if prof.get('location_mismatches',0)>0 else 0,
           0,1 if (amt>0 and amt%1000==0) else 0,0,
           round((amt-avg30)/(avg30+1),4),1 if amt>max7 else 0,
           round(math.log1p(amt),4),0.866,0.5,round(amt/(avg30+1),4),rp]
    p = model.predict_proba([vec])[0][1]
    print(f"  {recv:<16} ({note:<28}) -> fraud_prob={p:.4f}  score={int(p*100)}")

# Save model
model.save_model('app/ml_models/fraud_model.cbm')
print("\nModel saved to app/ml_models/fraud_model.cbm")
