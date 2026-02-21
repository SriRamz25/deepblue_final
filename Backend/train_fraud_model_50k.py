"""
Train fraud_model.cbm on the real 50,000-row hackathon dataset.
- Proper 80/20 train/test split (stratified)
- Engineers the 4 missing features to match the 22-feature schema
- Saves model to app/ml_models/fraud_model.cbm
- Prints full metrics for presentation
"""
import sys, os, math
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, accuracy_score, precision_score,
    recall_score, f1_score, classification_report, confusion_matrix
)

# ── Load ──────────────────────────────────────────────────────────────────────
CSV_PATH = os.path.join("..", "ML", "upi_fraud_hackathon_v4_replica_complete.csv")
print("Loading dataset:", CSV_PATH)
df = pd.read_csv(CSV_PATH)
print(f"Dataset shape : {df.shape}")
print(f"Fraud rate    : {df['is_fraud'].mean()*100:.2f}%  "
      f"({int(df['is_fraud'].sum())} fraud / {int((df['is_fraud']==0).sum())} legit)")
print()

# ── Engineer missing features ─────────────────────────────────────────────────
# txn_hour (0-23) → cyclical encoding + drop raw hour column
df['hour_sin']   = df['txn_hour'].apply(lambda h: round(math.sin(2 * math.pi * h / 24), 4))
df['hour_cos']   = df['txn_hour'].apply(lambda h: round(math.cos(2 * math.pi * h / 24), 4))
df['amount_log'] = df['amount'].apply(lambda a: round(math.log1p(a), 4))
df['ratio_30d']  = df.apply(lambda r: round(r['amount'] / (r['avg_amount_30d'] + 1), 4), axis=1)
# risk_profile: composite (receiver_type + location_mismatch + is_new_receiver), capped at 3
df['risk_profile'] = (df['receiver_type'] + df['location_mismatch'] + df['is_new_receiver']).clip(0, 3)

df.drop(columns=['txn_hour'], inplace=True)

# ── Feature columns in exact model schema order ───────────────────────────────
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

# ── Train / Test split (80/20, stratified) ────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train set : {len(X_train)} rows | fraud={int(y_train.sum())}")
print(f"Test  set : {len(X_test)} rows  | fraud={int(y_test.sum())}")
print()

# ── Train CatBoost ────────────────────────────────────────────────────────────
print("Training CatBoostClassifier ...")
model = CatBoostClassifier(
    iterations=500,
    learning_rate=0.05,
    depth=7,
    l2_leaf_reg=5,
    class_weights=[1, 19],   # 95:5 imbalance → weight fraud 19×
    random_seed=42,
    verbose=100,
)
model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=30)
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

print("=" * 56)
print("  MODEL PERFORMANCE ON TEST SET (10,000 rows)")
print("=" * 56)
print(f"  AUC-ROC   : {auc:.4f}")
print(f"  Accuracy  : {acc*100:.2f}%")
print(f"  Precision : {precision*100:.2f}%  (of flagged, how many are real fraud)")
print(f"  Recall    : {recall*100:.2f}%  (of all fraud, how many were caught)")
print(f"  F1 Score  : {f1:.4f}")
print()
print(f"  Confusion Matrix:")
print(f"               Predicted Legit   Predicted Fraud")
print(f"  Actual Legit    {cm[0][0]:>6}              {cm[0][1]:>5}")
print(f"  Actual Fraud    {cm[1][0]:>6}              {cm[1][1]:>5}")
print()
print(classification_report(y_test, y_pred, target_names=['Legit', 'Fraud']))
print("=" * 56)

# ── Feature importance (top 10) ───────────────────────────────────────────────
fi = model.get_feature_importance(prettified=True).head(10)
print("\nTop 10 Feature Importances:")
print(fi.to_string(index=False))
print()

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = "app/ml_models/fraud_model.cbm"
model.save_model(out_path)
print(f"Model saved → {out_path}")
print(f"Trees used  : {model.tree_count_}")
