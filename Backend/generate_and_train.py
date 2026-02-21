"""
Generates a 300k-row synthetic UPI fraud dataset with realistic
fraud/legit distributions, then trains CatBoost with proper
regularisation for high Precision + Recall + AUC.

Anti-overfitting techniques used:
  - Gaussian noise on every continuous feature
  - "Stealth fraud": 20% of fraud looks almost legit  
  - "Suspicious legit": 8% of legit has 1-2 fraud-like signals
  - 15% fraud rate → balanced enough for high precision
  - CatBoost early stopping on held-out test set
  - L2 regularisation + moderate depth
"""
import sys, os, math
sys.path.insert(0, ".")

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, accuracy_score, precision_score,
    recall_score, f1_score, classification_report, confusion_matrix
)

np.random.seed(42)

# ── Constants ─────────────────────────────────────────────────────────────────
N_TOTAL   = 300_000
FRAUD_RATE = 0.12          # 12% fraud
N_FRAUD   = int(N_TOTAL * FRAUD_RATE)
N_LEGIT   = N_TOTAL - N_FRAUD

print(f"Generating {N_TOTAL:,} rows  ({N_FRAUD:,} fraud, {N_LEGIT:,} legit) with realistic overlap...")

def noise(arr, scale):
    return arr + np.random.normal(0, scale, size=len(arr))

# ─────────────────────────────────────────────────────────────────────────────
# LEGIT transactions
# ─────────────────────────────────────────────────────────────────────────────
def gen_legit(n):
    # Amounts follow lognormal (median ~3,000, up to ~50k)
    amount = np.clip(np.random.lognormal(mean=8.0, sigma=1.4, size=n), 50, 200_000)

    avg_amount_30d = np.clip(noise(amount * np.random.uniform(0.6, 1.5, n), amount*0.10), 500, 200_000)
    avg_amount_7d  = np.clip(noise(avg_amount_30d * np.random.uniform(0.7, 1.4, n), avg_amount_30d*0.10), 500, 200_000)
    max_amount_7d  = np.clip(avg_amount_7d * np.random.uniform(1.0, 3.0, n), avg_amount_7d, 300_000)

    txn_count_1h   = np.random.choice([0,1,2,3], p=[0.60,0.25,0.10,0.05], size=n)
    txn_count_24h  = np.random.randint(0, 12, size=n)
    days_since     = np.clip(np.random.exponential(6, n), 0, 90).astype(int)
    night_ratio    = np.clip(noise(np.random.beta(1.5, 8, n), 0.04), 0, 1)

    payment_mode   = np.random.choice([0,1,2], p=[0.55,0.30,0.15], size=n)
    receiver_type  = np.random.choice([0,1],   p=[0.80,0.20], size=n)
    is_new_recv    = np.random.choice([0,1],   p=[0.85,0.15], size=n)

    location_mm    = np.random.choice([0,1], p=[0.88,0.12], size=n)
    is_night       = np.random.choice([0,1], p=[0.88,0.12], size=n)
    is_round       = np.random.choice([0,1], p=[0.80,0.20], size=n)
    velocity_check = (txn_count_1h > 2).astype(int)

    dev = np.clip(noise((amount - avg_amount_30d) / (avg_amount_30d + 1), 0.3), -2, 10)
    exceeds_max    = (amount > max_amount_7d).astype(int)
    amount_log     = np.log1p(amount)
    hour           = np.random.randint(0, 24, n)
    hour_sin       = np.sin(2 * math.pi * hour / 24)
    hour_cos       = np.cos(2 * math.pi * hour / 24)
    ratio_30d      = np.clip(amount / (avg_amount_30d + 1), 0, 15)
    risk_profile   = np.clip(receiver_type + location_mm + is_new_recv, 0, 3)

    # 20% "suspicious legit" — inject 1-2 fraud-like signals to create genuine overlap
    suspicious_idx = np.random.choice(n, size=int(n*0.20), replace=False)
    for idx in suspicious_idx:
        num_signals = np.random.choice([1, 2], p=[0.70, 0.30])
        fields = np.random.choice([0,1,2,3,4], size=num_signals, replace=False)
        for field in fields:
            if field == 0: location_mm[idx] = 1
            elif field == 1: is_new_recv[idx] = 1
            elif field == 2: velocity_check[idx] = 1
            elif field == 3: is_night[idx] = 1
            else: receiver_type[idx] = 1

    return {
        'amount': amount, 'payment_mode': payment_mode,
        'receiver_type': receiver_type, 'is_new_receiver': is_new_recv,
        'avg_amount_7d': avg_amount_7d, 'avg_amount_30d': avg_amount_30d,
        'max_amount_7d': max_amount_7d, 'txn_count_1h': txn_count_1h,
        'txn_count_24h': txn_count_24h, 'days_since_last_txn': days_since,
        'night_txn_ratio': night_ratio, 'location_mismatch': location_mm,
        'is_night': is_night, 'is_round_amount': is_round,
        'velocity_check': velocity_check,
        'deviation_from_sender_avg': dev, 'exceeds_recent_max': exceeds_max,
        'amount_log': amount_log, 'hour_sin': hour_sin, 'hour_cos': hour_cos,
        'ratio_30d': ratio_30d, 'risk_profile': risk_profile,
        'is_fraud': np.zeros(n, dtype=int),
    }

# ─────────────────────────────────────────────────────────────────────────────
# FRAUD transactions
# ─────────────────────────────────────────────────────────────────────────────
def gen_fraud(n):
    # Fraud amounts: mostly overlapping with legit, with a long tail of high amounts
    # 60% of fraud looks amount-wise identical to legit
    legit_like_n = int(n * 0.60)
    large_n      = n - legit_like_n
    amount_ll = np.clip(np.random.lognormal(mean=8.0, sigma=1.4, size=legit_like_n), 50, 200_000)
    amount_lg = np.clip(np.random.uniform(30_000, 250_000, large_n), 30_000, 250_000)
    amount    = np.concatenate([amount_ll, amount_lg])
    np.random.shuffle(amount)

    # Sender avg very similar to legit — hard for model to separate
    avg_amount_30d = np.clip(noise(amount * np.random.uniform(0.5, 2.0, n), amount*0.15), 500, 200_000)
    avg_amount_7d  = np.clip(noise(avg_amount_30d * np.random.uniform(0.6, 1.5, n), avg_amount_30d*0.12), 500, 200_000)
    max_amount_7d  = avg_amount_7d * np.random.uniform(0.8, 3.0, n)

    # Key: fraud transaction counts heavily overlap with legit
    txn_count_1h   = np.random.choice([0,1,2,3,4,5], p=[0.30,0.25,0.20,0.13,0.08,0.04], size=n)
    txn_count_24h  = np.random.randint(0, 15, size=n)
    days_since     = np.clip(np.random.exponential(4, n), 0, 60).astype(int)
    # night_ratio: fraud slightly higher but largely overlapping
    night_ratio    = np.clip(noise(np.random.beta(2.5, 6, n), 0.07), 0, 1)

    payment_mode   = np.random.choice([0,1,2], p=[0.45,0.32,0.23], size=n)
    receiver_type  = np.random.choice([0,1],   p=[0.45,0.55], size=n)
    is_new_recv    = np.random.choice([0,1],   p=[0.42,0.58], size=n)

    location_mm    = np.random.choice([0,1], p=[0.52,0.48], size=n)
    is_night       = np.random.choice([0,1], p=[0.72,0.28], size=n)
    is_round       = np.random.choice([0,1], p=[0.50,0.50], size=n)
    velocity_check = (txn_count_1h > 2).astype(int)

    dev = np.clip(noise((amount - avg_amount_30d) / (avg_amount_30d + 1), 0.8), -3, 20)
    exceeds_max    = (amount > max_amount_7d).astype(int)
    amount_log     = np.log1p(amount)
    hour           = np.random.randint(0, 24, n)
    hour_sin       = np.sin(2 * math.pi * hour / 24)
    hour_cos       = np.cos(2 * math.pi * hour / 24)
    ratio_30d      = np.clip(amount / (avg_amount_30d + 1), 0, 30)
    risk_profile   = np.clip(receiver_type + location_mm + is_new_recv, 0, 3)

    # 55% "stealth fraud" — look nearly identical to legit
    stealth_idx = np.random.choice(n, size=int(n*0.55), replace=False)
    for idx in stealth_idx:
        location_mm[idx]    = np.random.choice([0,1], p=[0.75,0.25])
        velocity_check[idx] = 0
        is_new_recv[idx]    = np.random.choice([0,1], p=[0.65,0.35])
        receiver_type[idx]  = np.random.choice([0,1], p=[0.60,0.40])
        dev[idx]            = np.clip(dev[idx] * np.random.uniform(0.05, 0.4), -1, 3)
        risk_profile[idx]   = max(0, risk_profile[idx] - 1)

    return {
        'amount': amount, 'payment_mode': payment_mode,
        'receiver_type': receiver_type, 'is_new_receiver': is_new_recv,
        'avg_amount_7d': avg_amount_7d, 'avg_amount_30d': avg_amount_30d,
        'max_amount_7d': max_amount_7d, 'txn_count_1h': txn_count_1h,
        'txn_count_24h': txn_count_24h, 'days_since_last_txn': days_since,
        'night_txn_ratio': night_ratio, 'location_mismatch': location_mm,
        'is_night': is_night, 'is_round_amount': is_round,
        'velocity_check': velocity_check,
        'deviation_from_sender_avg': dev, 'exceeds_recent_max': exceeds_max,
        'amount_log': amount_log, 'hour_sin': hour_sin, 'hour_cos': hour_cos,
        'ratio_30d': ratio_30d, 'risk_profile': risk_profile,
        'is_fraud': np.ones(n, dtype=int),
    }

# ── Build DataFrame ───────────────────────────────────────────────────────────
df = pd.concat([
    pd.DataFrame(gen_legit(N_LEGIT)),
    pd.DataFrame(gen_fraud(N_FRAUD)),
], ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)

print(f"Dataset ready : {len(df):,} rows")
print(f"Fraud rate    : {df['is_fraud'].mean()*100:.1f}%  "
      f"({int(df['is_fraud'].sum()):,} fraud / {int((df['is_fraud']==0).sum()):,} legit)")
print()

# ── Feature / Label split ─────────────────────────────────────────────────────
FEATURE_COLS = [
    'amount', 'payment_mode', 'receiver_type', 'is_new_receiver',
    'avg_amount_7d', 'avg_amount_30d', 'max_amount_7d',
    'txn_count_1h', 'txn_count_24h', 'days_since_last_txn',
    'night_txn_ratio', 'location_mismatch', 'is_night', 'is_round_amount',
    'velocity_check', 'deviation_from_sender_avg', 'exceeds_recent_max',
    'amount_log', 'hour_sin', 'hour_cos', 'ratio_30d', 'risk_profile',
]
X = df[FEATURE_COLS]
y = df['is_fraud']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
print(f"Train : {len(X_train):,} rows  |  Test : {len(X_test):,} rows")
print()

# ── Train CatBoost ────────────────────────────────────────────────────────────
print("Training CatBoost ...")
model = CatBoostClassifier(
    iterations      = 500,
    learning_rate   = 0.07,
    depth           = 5,
    l2_leaf_reg     = 15,       # strong regularisation
    min_data_in_leaf= 100,      # prevents overfitting on noisy leaves
    class_weights   = [1, 4],   # fraud is 12% → upweight 4× (lower → better precision)
    random_seed     = 42,
    verbose         = 100,
)
model.fit(
    X_train, y_train,
    eval_set=(X_test, y_test),
    early_stopping_rounds=40,
)
print()

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred  = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

auc       = roc_auc_score(y_test, y_proba)
acc       = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
cm        = confusion_matrix(y_test, y_pred)

print("=" * 60)
print("  FINAL MODEL METRICS  (Test set — 60,000 rows)")
print("=" * 60)
print(f"  AUC-ROC   : {auc:.4f}")
print(f"  Accuracy  : {acc*100:.2f}%")
print(f"  Precision : {precision*100:.2f}%")
print(f"  Recall    : {recall*100:.2f}%")
print(f"  F1 Score  : {f1:.4f}")
print()
print(f"  Confusion Matrix:")
print(f"               Predicted Legit   Predicted Fraud")
print(f"  Actual Legit    {cm[0][0]:>7,}           {cm[0][1]:>7,}")
print(f"  Actual Fraud    {cm[1][0]:>7,}           {cm[1][1]:>7,}")
print()
print(classification_report(y_test, y_pred, target_names=['Legit','Fraud']))
print("=" * 60)

# ── Feature importance ────────────────────────────────────────────────────────
fi = model.get_feature_importance(prettified=True).head(10)
print("\nTop 10 Feature Importances:")
print(fi.to_string(index=False))

# ── Save Model ───────────────────────────────────────────────────────────────
model.save_model("app/ml_models/fraud_model.cbm")
print(f"\nModel saved → app/ml_models/fraud_model.cbm")
print(f"Trees used  : {model.tree_count_}")

# ── Save Dataset ──────────────────────────────────────────────────────────────
DATASET_OUT = os.path.join("..", "ML", "upi_fraud_300k_synthetic.csv")
df.to_csv(DATASET_OUT, index=False)
print(f"Dataset saved → {DATASET_OUT}  ({len(df):,} rows)")
