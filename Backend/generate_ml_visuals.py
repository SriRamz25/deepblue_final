"""
Generate ML visualisation artefacts for the Sentra Pay fraud model:
  1.  Confusion Matrix
  2.  ROC Curve
  3.  Training vs Validation Loss Curve
  4.  Feature Importance (top 15)
  5.  Precision-Recall Curve

All PNGs saved to  Backend/static/ml_visuals/

NOTE: Regenerates the same 300k synthetic dataset (seed=42) used during
training so the test split is identical to training time.
"""

import os, sys, math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, accuracy_score, precision_score,
    recall_score, f1_score, classification_report,
    confusion_matrix, roc_curve, precision_recall_curve, average_precision_score
)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE   = os.path.dirname(os.path.abspath(__file__))
MODEL  = os.path.join(BASE, "app", "ml_models", "fraud_model.cbm")
OUT    = os.path.join(BASE, "static", "ml_visuals")
LEARN  = os.path.join(BASE, "catboost_info", "learn_error.tsv")
TEST_E = os.path.join(BASE, "catboost_info", "test_error.tsv")

os.makedirs(OUT, exist_ok=True)

DARK_BG   = "#0F1117"
CARD_BG   = "#1A1A2E"
ACCENT    = "#4F8EF7"
FRAUD_CLR = "#FF4757"
SAFE_CLR  = "#2ED573"
TEXT_CLR  = "#CDD6F4"
GRID_CLR  = "#2A2A3E"

plt.rcParams.update({
    "figure.facecolor":  DARK_BG,
    "axes.facecolor":    CARD_BG,
    "axes.edgecolor":    GRID_CLR,
    "axes.labelcolor":   TEXT_CLR,
    "xtick.color":       TEXT_CLR,
    "ytick.color":       TEXT_CLR,
    "text.color":        TEXT_CLR,
    "grid.color":        GRID_CLR,
    "grid.linewidth":    0.5,
    "font.family":       "DejaVu Sans",
})

# ── Regenerate same 300k dataset (seed=42 matches training) ───────────────────
print("Regenerating 300k synthetic dataset (same seed as training) …")
np.random.seed(42)
N_TOTAL = 300_000; FRAUD_RATE = 0.12
N_FRAUD = int(N_TOTAL * FRAUD_RATE); N_LEGIT = N_TOTAL - N_FRAUD

def noise(arr, scale): return arr + np.random.normal(0, scale, size=len(arr))

def gen_legit(n):
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
    return {'amount': amount, 'payment_mode': payment_mode, 'receiver_type': receiver_type,
            'is_new_receiver': is_new_recv, 'avg_amount_7d': avg_amount_7d,
            'avg_amount_30d': avg_amount_30d, 'max_amount_7d': max_amount_7d,
            'txn_count_1h': txn_count_1h, 'txn_count_24h': txn_count_24h,
            'days_since_last_txn': days_since, 'night_txn_ratio': night_ratio,
            'location_mismatch': location_mm, 'is_night': is_night,
            'is_round_amount': is_round, 'velocity_check': velocity_check,
            'deviation_from_sender_avg': dev, 'exceeds_recent_max': exceeds_max,
            'amount_log': amount_log, 'hour_sin': hour_sin, 'hour_cos': hour_cos,
            'ratio_30d': ratio_30d, 'risk_profile': risk_profile,
            'is_fraud': np.zeros(n, dtype=int)}

def gen_fraud(n):
    legit_like_n = int(n * 0.60); large_n = n - legit_like_n
    amount_ll = np.clip(np.random.lognormal(mean=8.0, sigma=1.4, size=legit_like_n), 50, 200_000)
    amount_lg = np.clip(np.random.uniform(30_000, 250_000, large_n), 30_000, 250_000)
    amount    = np.concatenate([amount_ll, amount_lg]); np.random.shuffle(amount)
    avg_amount_30d = np.clip(noise(amount * np.random.uniform(0.5, 2.0, n), amount*0.15), 500, 200_000)
    avg_amount_7d  = np.clip(noise(avg_amount_30d * np.random.uniform(0.6, 1.5, n), avg_amount_30d*0.12), 500, 200_000)
    max_amount_7d  = avg_amount_7d * np.random.uniform(0.8, 3.0, n)
    txn_count_1h   = np.random.choice([0,1,2,3,4,5], p=[0.30,0.25,0.20,0.13,0.08,0.04], size=n)
    txn_count_24h  = np.random.randint(0, 15, size=n)
    days_since     = np.clip(np.random.exponential(4, n), 0, 60).astype(int)
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
    stealth_idx = np.random.choice(n, size=int(n*0.55), replace=False)
    for idx in stealth_idx:
        location_mm[idx]    = np.random.choice([0,1], p=[0.75,0.25])
        velocity_check[idx] = 0
        is_new_recv[idx]    = np.random.choice([0,1], p=[0.65,0.35])
        receiver_type[idx]  = np.random.choice([0,1], p=[0.60,0.40])
        dev[idx]            = np.clip(dev[idx] * np.random.uniform(0.05, 0.4), -1, 3)
        risk_profile[idx]   = max(0, risk_profile[idx] - 1)
    return {'amount': amount, 'payment_mode': payment_mode, 'receiver_type': receiver_type,
            'is_new_receiver': is_new_recv, 'avg_amount_7d': avg_amount_7d,
            'avg_amount_30d': avg_amount_30d, 'max_amount_7d': max_amount_7d,
            'txn_count_1h': txn_count_1h, 'txn_count_24h': txn_count_24h,
            'days_since_last_txn': days_since, 'night_txn_ratio': night_ratio,
            'location_mismatch': location_mm, 'is_night': is_night,
            'is_round_amount': is_round, 'velocity_check': velocity_check,
            'deviation_from_sender_avg': dev, 'exceeds_recent_max': exceeds_max,
            'amount_log': amount_log, 'hour_sin': hour_sin, 'hour_cos': hour_cos,
            'ratio_30d': ratio_30d, 'risk_profile': risk_profile,
            'is_fraud': np.ones(n, dtype=int)}

df = pd.concat([pd.DataFrame(gen_legit(N_LEGIT)), pd.DataFrame(gen_fraud(N_FRAUD))],
               ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)

FEATURE_COLS = [
    'amount','payment_mode','receiver_type','is_new_receiver',
    'avg_amount_7d','avg_amount_30d','max_amount_7d',
    'txn_count_1h','txn_count_24h','days_since_last_txn',
    'night_txn_ratio','location_mismatch','is_night','is_round_amount',
    'velocity_check','deviation_from_sender_avg','exceeds_recent_max',
    'amount_log','hour_sin','hour_cos','ratio_30d','risk_profile',
]
X = df[FEATURE_COLS]; y = df['is_fraud']
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Dataset: {len(df):,} rows | Test set: {len(X_test):,} rows")

# ── Load Model ────────────────────────────────────────────────────────────────
print("Loading model …")
model = CatBoostClassifier()
model.load_model(MODEL)

y_pred  = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

# ── Core Metrics ──────────────────────────────────────────────────────────────
auc       = roc_auc_score(y_test, y_proba)
acc       = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
cm        = confusion_matrix(y_test, y_pred)
ap        = average_precision_score(y_test, y_proba)

print("\n" + "═"*56)
print("  SENTRA PAY — FRAUD MODEL METRICS (Test: 60,000 rows)")
print("═"*56)
print(f"  AUC-ROC    : {auc:.4f}")
print(f"  Accuracy   : {acc*100:.2f}%")
print(f"  Precision  : {precision*100:.2f}%")
print(f"  Recall     : {recall*100:.2f}%")
print(f"  F1 Score   : {f1:.4f}")
print(f"  Avg Prec.  : {ap:.4f}")
print()
print(f"  Confusion Matrix:")
print(f"                   Predicted Legit   Predicted Fraud")
print(f"  Actual  Legit       {cm[0][0]:>7}            {cm[0][1]:>7}")
print(f"  Actual  Fraud       {cm[1][0]:>7}            {cm[1][1]:>7}")
print()
print(classification_report(y_test, y_pred, target_names=['Legit','Fraud']))
print("═"*56)

fi_df = model.get_feature_importance(prettified=True)
print("\nTop 15 Feature Importances:")
print(fi_df.head(15).to_string(index=False))


# ══════════════════════════════════════════════════════════════════════════════
# 1.  CONFUSION MATRIX
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 6))
fig.patch.set_facecolor(DARK_BG)
ax.set_facecolor(CARD_BG)

labels = [["TN\n(Legit → Legit)", "FP\n(Legit → Fraud)"],
          ["FN\n(Fraud → Legit)", "TP\n(Fraud → Fraud)"]]
colors  = [[SAFE_CLR, FRAUD_CLR], [FRAUD_CLR, SAFE_CLR]]
alphas  = [[0.25, 0.15], [0.15, 0.35]]

for i in range(2):
    for j in range(2):
        ax.add_patch(plt.Rectangle((j-0.5, 1.5-i-0.5), 1, 1,
                                    color=colors[i][j], alpha=alphas[i][j]))
        ax.text(j, 1-i, f"{cm[i][j]:,}\n{labels[i][j]}",
                ha='center', va='center', fontsize=14,
                fontweight='bold', color=TEXT_CLR)

ax.set_xlim(-0.5, 1.5)
ax.set_ylim(-0.5, 1.5)
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xticklabels(['Predicted\nLegit', 'Predicted\nFraud'], fontsize=11)
ax.set_yticklabels(['Actual\nFraud', 'Actual\nLegit'], fontsize=11)
ax.set_title("Confusion Matrix — Sentra Pay Fraud Model",
             fontsize=14, fontweight='bold', color=TEXT_CLR, pad=20)

# Metric annotations
meta = (f"Precision: {precision*100:.1f}%   Recall: {recall*100:.1f}%   "
        f"F1: {f1:.3f}   AUC: {auc:.4f}")
fig.text(0.5, 0.01, meta, ha='center', fontsize=10, color=ACCENT)

plt.tight_layout(rect=[0, 0.04, 1, 1])
p1 = os.path.join(OUT, "confusion_matrix.png")
plt.savefig(p1, dpi=150, bbox_inches='tight')
plt.close()
print(f"\n✅ Saved: {p1}")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  ROC CURVE
# ══════════════════════════════════════════════════════════════════════════════
fpr, tpr, _ = roc_curve(y_test, y_proba)

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(fpr, tpr, color=ACCENT, lw=2.5,
        label=f"CatBoost (AUC = {auc:.4f})")
ax.plot([0,1],[0,1], color=GRID_CLR, lw=1, linestyle='--', label='Random (AUC = 0.50)')
ax.fill_between(fpr, tpr, alpha=0.12, color=ACCENT)
ax.set_xlabel("False Positive Rate", fontsize=13)
ax.set_ylabel("True Positive Rate", fontsize=13)
ax.set_title("ROC Curve — Sentra Pay Fraud Detection", fontsize=14, fontweight='bold', pad=16)
ax.legend(fontsize=11, facecolor=CARD_BG, edgecolor=GRID_CLR)
ax.grid(True, alpha=0.4)
ax.set_xlim([0,1]); ax.set_ylim([0,1.02])
plt.tight_layout()
p2 = os.path.join(OUT, "roc_curve.png")
plt.savefig(p2, dpi=150, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {p2}")


# ══════════════════════════════════════════════════════════════════════════════
# 3.  TRAINING vs VALIDATION LOSS CURVE
# ══════════════════════════════════════════════════════════════════════════════
learn_df = pd.read_csv(LEARN, sep='\t')
test_df  = pd.read_csv(TEST_E, sep='\t')

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(learn_df['iter'], learn_df['Logloss'],
        color=SAFE_CLR, lw=2, label='Train Loss')
ax.plot(test_df['iter'],  test_df['Logloss'],
        color=ACCENT, lw=2, linestyle='--', label='Validation Loss')
ax.set_xlabel("Iteration", fontsize=13)
ax.set_ylabel("Log Loss", fontsize=13)
ax.set_title("Training vs Validation Loss — CatBoost (500 iterations)",
             fontsize=14, fontweight='bold', pad=16)
ax.legend(fontsize=11, facecolor=CARD_BG, edgecolor=GRID_CLR)
ax.grid(True, alpha=0.4)
min_val = test_df['Logloss'].min()
min_iter= test_df.loc[test_df['Logloss'].idxmin(), 'iter']
ax.axvline(min_iter, color=FRAUD_CLR, lw=1, linestyle=':',
           label=f'Best val @ iter {min_iter}: {min_val:.4f}')
ax.legend(fontsize=10, facecolor=CARD_BG, edgecolor=GRID_CLR)
plt.tight_layout()
p3 = os.path.join(OUT, "loss_curve.png")
plt.savefig(p3, dpi=150, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {p3}")


# ══════════════════════════════════════════════════════════════════════════════
# 4.  FEATURE IMPORTANCE (top 15)
# ══════════════════════════════════════════════════════════════════════════════
top15 = fi_df.head(15).sort_values('Importances')
names  = top15['Feature Id'].tolist()
vals   = top15['Importances'].tolist()

bar_colors = [FRAUD_CLR if v > 15 else (ACCENT if v > 7 else SAFE_CLR) for v in vals]

fig, ax = plt.subplots(figsize=(9, 7))
bars = ax.barh(names, vals, color=bar_colors, edgecolor='none', height=0.65)
for bar, v in zip(bars, vals):
    ax.text(v + 0.3, bar.get_y() + bar.get_height()/2,
            f"{v:.1f}%", va='center', fontsize=10, color=TEXT_CLR)
ax.set_xlabel("Feature Importance (%)", fontsize=12)
ax.set_title("Top 15 Feature Importances — Sentra Pay Fraud Model",
             fontsize=14, fontweight='bold', pad=16)
ax.grid(True, axis='x', alpha=0.4)
legend_patches = [
    mpatches.Patch(color=FRAUD_CLR, label='High (>15%)'),
    mpatches.Patch(color=ACCENT,    label='Medium (>7%)'),
    mpatches.Patch(color=SAFE_CLR,  label='Low (≤7%)'),
]
ax.legend(handles=legend_patches, fontsize=10, facecolor=CARD_BG, edgecolor=GRID_CLR)
plt.tight_layout()
p4 = os.path.join(OUT, "feature_importance.png")
plt.savefig(p4, dpi=150, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {p4}")


# ══════════════════════════════════════════════════════════════════════════════
# 5.  PRECISION-RECALL CURVE
# ══════════════════════════════════════════════════════════════════════════════
prec_curve, rec_curve, _ = precision_recall_curve(y_test, y_proba)
baseline = y_test.mean()

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(rec_curve, prec_curve, color=FRAUD_CLR, lw=2.5,
        label=f"CatBoost (AP = {ap:.4f})")
ax.axhline(baseline, color=GRID_CLR, lw=1, linestyle='--',
           label=f'Random (Baseline = {baseline:.3f})')
ax.fill_between(rec_curve, prec_curve, alpha=0.12, color=FRAUD_CLR)
ax.set_xlabel("Recall", fontsize=13)
ax.set_ylabel("Precision", fontsize=13)
ax.set_title("Precision-Recall Curve — Sentra Pay Fraud Detection",
             fontsize=14, fontweight='bold', pad=16)
ax.legend(fontsize=11, facecolor=CARD_BG, edgecolor=GRID_CLR)
ax.grid(True, alpha=0.4)
ax.set_xlim([0,1]); ax.set_ylim([0,1.02])
plt.tight_layout()
p5 = os.path.join(OUT, "precision_recall_curve.png")
plt.savefig(p5, dpi=150, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {p5}")


# ══════════════════════════════════════════════════════════════════════════════
# 6.  SUMMARY DASHBOARD  (all 4 in a 2×2 grid)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.patch.set_facecolor(DARK_BG)
fig.suptitle("Sentra Pay — ML Model Dashboard", fontsize=18,
             fontweight='bold', color=TEXT_CLR, y=0.98)

# ── top-left: Confusion Matrix ────────────────────────────────────────────────
ax = axes[0][0]
ax.set_facecolor(CARD_BG)
for i in range(2):
    for j in range(2):
        ax.add_patch(plt.Rectangle((j-0.5, 1.5-i-0.5), 1, 1,
                                    color=colors[i][j], alpha=alphas[i][j]))
        ax.text(j, 1-i, f"{cm[i][j]:,}\n{labels[i][j]}",
                ha='center', va='center', fontsize=12,
                fontweight='bold', color=TEXT_CLR)
ax.set_xlim(-0.5, 1.5); ax.set_ylim(-0.5, 1.5)
ax.set_xticks([0,1]); ax.set_yticks([0,1])
ax.set_xticklabels(['Pred Legit','Pred Fraud'], fontsize=10)
ax.set_yticklabels(['Act Fraud','Act Legit'], fontsize=10)
ax.set_title("Confusion Matrix", fontsize=13, fontweight='bold', color=TEXT_CLR, pad=10)

# ── top-right: ROC Curve ──────────────────────────────────────────────────────
ax = axes[0][1]
ax.plot(fpr, tpr, color=ACCENT, lw=2, label=f"AUC = {auc:.4f}")
ax.plot([0,1],[0,1], color=GRID_CLR, lw=1, linestyle='--')
ax.fill_between(fpr, tpr, alpha=0.1, color=ACCENT)
ax.set_xlabel("FPR", fontsize=11); ax.set_ylabel("TPR", fontsize=11)
ax.set_title("ROC Curve", fontsize=13, fontweight='bold', color=TEXT_CLR, pad=10)
ax.legend(fontsize=10, facecolor=CARD_BG, edgecolor=GRID_CLR)
ax.grid(True, alpha=0.3)

# ── bottom-left: Loss Curve ───────────────────────────────────────────────────
ax = axes[1][0]
ax.plot(learn_df['iter'], learn_df['Logloss'], color=SAFE_CLR, lw=1.8, label='Train')
ax.plot(test_df['iter'],  test_df['Logloss'],  color=ACCENT, lw=1.8, linestyle='--', label='Validation')
ax.axvline(min_iter, color=FRAUD_CLR, lw=1, linestyle=':')
ax.set_xlabel("Iteration", fontsize=11); ax.set_ylabel("Log Loss", fontsize=11)
ax.set_title("Loss Curve (500 Iterations)", fontsize=13, fontweight='bold', color=TEXT_CLR, pad=10)
ax.legend(fontsize=10, facecolor=CARD_BG, edgecolor=GRID_CLR)
ax.grid(True, alpha=0.3)

# ── bottom-right: Feature Importance ─────────────────────────────────────────
ax = axes[1][1]
ax.barh(names, vals, color=bar_colors, edgecolor='none', height=0.65)
for v, name in zip(vals, names):
    ax.text(v + 0.2, names.index(name), f"{v:.1f}%", va='center', fontsize=9, color=TEXT_CLR)
ax.set_xlabel("Importance (%)", fontsize=11)
ax.set_title("Top 15 Feature Importances", fontsize=13, fontweight='bold', color=TEXT_CLR, pad=10)
ax.grid(True, axis='x', alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.96])
p6 = os.path.join(OUT, "ml_dashboard.png")
plt.savefig(p6, dpi=150, bbox_inches='tight')
plt.close()
print(f"✅ Saved: {p6}")

print(f"\n🎉 All visuals saved to: {OUT}")
