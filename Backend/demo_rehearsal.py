"""
╔══════════════════════════════════════════════════════════════════════════╗
║              SENTRAPAY — DEMO REHEARSAL SCRIPT                          ║
║  Runs the REAL risk engines against REAL CSV data.                      ║
║  Know your results BEFORE showing judges. No surprises.                 ║
╚══════════════════════════════════════════════════════════════════════════╝

Usage:
    cd SentraPay_Backup_20250220/Backend
    python demo_rehearsal.py

This calls the SAME 3 engines the live app calls.
Output = exactly what the Flutter UI will show.
"""

import sys
import os
from datetime import datetime

# ── Set up sys.path and stub required env vars before importing app modules ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Provide dummy required env vars so pydantic_settings.BaseSettings doesn't error
os.environ.setdefault("DATABASE_URL",  "sqlite:///./dummy_demo.db")
os.environ.setdefault("REDIS_URL",     "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY",    "demo-secret-key-rehearsal")
os.environ.setdefault("SENDER_CSV_PATH",   "demo_data/sender_history.csv")
os.environ.setdefault("RECEIVER_CSV_PATH", "demo_data/receiver_history (2).csv")

import pandas as pd

# Now safe to import the real engines
from app.core.data_loader import load_sender_history, get_sender_stats, get_receiver_profile
from app.core.relationship_engine import analyze_user_relationship
from app.core.amount_risk_engine import analyze_amount_risk
from app.core.receiver_ml_engine import analyze_receiver_risk
from app.core.final_risk_engine import compute_final_risk

# ─────────────────────────────────────────────────────────────
# DEMO SCENARIOS
# Each entry = one transaction you will demonstrate live.
# ─────────────────────────────────────────────────────────────
# Columns:
#   label       : name shown in output
#   sender_upi  : who sends
#   receiver_upi: who receives
#   amount      : transaction amount (₹)
#   demo_time   : simulate it at this datetime hour (affects is_night)
# ─────────────────────────────────────────────────────────────
DEMO_SCENARIOS = [
    # ── SCENARIO 1: Trusted receiver, clean history → LOW ─────────
    {
        "label": "SCENARIO 1 — Regular payment to a familiar contact",
        "sender_upi": "user1@upi",       # avg ₹3,700, paid recv1 5 times
        "receiver_upi": "recv1@upi",     # ffr=0.00 (completely clean)
        "amount": 3500,
        "demo_time": datetime(2026, 2, 20, 10, 30),   # daytime
    },

    # ── SCENARIO 2: First time + mixed receiver + moderate spike → MODERATE ──
    {
        "label": "SCENARIO 2 — First payment to a semi-flagged contact",
        "sender_upi": "user3@upi",       # avg ₹720, pays recv9 5 times (not recv5)
        "receiver_upi": "recv5@upi",     # ffr=0.50 (mixed fraud history)
        "amount": 2500,
        "demo_time": datetime(2026, 2, 20, 14, 0),    # afternoon
    },

    # ── SCENARIO 3: First-ever + fraud receiver + big spike → HIGH ─
    {
        "label": "SCENARIO 3 — Large transfer to a known fraud receiver",
        "sender_upi": "user1@upi",       # avg ₹3,700
        "receiver_upi": "recv6@upi",     # ffr=1.00 (100% fraud flagged)
        "amount": 20000,
        "demo_time": datetime(2026, 2, 20, 11, 0),
    },

    # ── SCENARIO 4: Night + fraud receiver + massive spike → HIGH (max) ──
    {
        "label": "SCENARIO 4 — Night-time transfer to fraud receiver",
        "sender_upi": "user3@upi",       # avg ₹720 — low avg makes ratio huge
        "receiver_upi": "recv8@upi",     # ffr=1.00 (100% fraud flagged)
        "amount": 15000,
        "demo_time": datetime(2026, 2, 20, 2, 30),    # 2:30 AM — night
    },
]


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
RISK_COLORS = {
    "LOW":      "\033[92m",   # green
    "MODERATE": "\033[93m",   # yellow
    "HIGH":     "\033[91m",   # red
    "CRITICAL": "\033[95m",   # magenta
}
RESET = "\033[0m"
BOLD  = "\033[1m"

ACTION_EMOJI = {
    "ALLOW": "✅ ALLOW",
    "WARN":  "⚠️  WARN",
    "OTP":   "🔐 OTP Required",
    "BLOCK": "🚫 BLOCK (flag receiver)",
}

def _bar(score: int, width: int = 30) -> str:
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)

def _color(level: str, text: str) -> str:
    return RISK_COLORS.get(level, "") + text + RESET

def run_scenario(s: dict) -> dict:
    """Run all 3 layers for a single scenario. Returns full result."""
    sender_upi   = s["sender_upi"]
    receiver_upi = s["receiver_upi"]
    amount       = s["amount"]
    demo_time    = s["demo_time"]

    # Load sender data
    sender_df  = load_sender_history()
    txn_stats  = get_sender_stats(sender_upi, now=demo_time)
    recv_prof  = get_receiver_profile(receiver_upi)

    # ── Layer 1: Relationship ────────────────
    l1 = analyze_user_relationship(
        sender_upi=sender_upi,
        receiver_upi=receiver_upi,
        history_df=sender_df,
        now=demo_time,
    )

    # ── Layer 2: Amount ──────────────────────
    l2 = analyze_amount_risk(amount, txn_stats)

    # ── Layer 3: Receiver ML ─────────────────
    txn_data_for_ml = {
        "amount": amount,
        "receiver": receiver_upi,
        "timestamp": demo_time.isoformat(),
    }
    context_for_ml = {
        **txn_stats,
        "fraud_flag_ratio":        recv_prof.get("fraud_flag_ratio", 0.0),
        "impossible_travel_count": recv_prof.get("impossible_travel_count", 0),
        "location_mismatch":       recv_prof.get("location_mismatches", 0),
    }
    l3 = analyze_receiver_risk(txn_data_for_ml, context_for_ml, model=None)

    # ── Final combination ────────────────────
    final = compute_final_risk(
        user_score     = l1["user_risk_score"],
        amount_score   = l2["amount_risk_score"],
        receiver_score = l3["receiver_risk_score"],
    )

    return {
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "final": final,
        "txn_stats": txn_stats,
        "recv_prof": recv_prof,
    }


# ─────────────────────────────────────────────────────────────
# MAIN PRINTER
# ─────────────────────────────────────────────────────────────
def print_header():
    print()
    print(BOLD + "═" * 70 + RESET)
    print(BOLD + "   SENTRAPAY  —  DEMO REHEARSAL RESULTS" + RESET)
    print(BOLD + "   All scores computed by the LIVE ENGINE (same as the app)" + RESET)
    print(BOLD + "═" * 70 + RESET)
    print()


def print_scenario(label: str, s: dict, result: dict):
    final    = result["final"]
    l1       = result["l1"]
    l2       = result["l2"]
    l3       = result["l3"]
    stats    = result["txn_stats"]
    recv     = result["recv_prof"]

    risk_level = final["risk_level"]
    color      = RISK_COLORS.get(risk_level, "")

    print(BOLD + "─" * 70 + RESET)
    print(BOLD + f"  {label}" + RESET)
    print(f"  Sender   : {s['sender_upi']}")
    print(f"  Receiver : {s['receiver_upi']}")
    print(f"  Amount   : ₹{s['amount']:,}")
    print(f"  Time     : {s['demo_time'].strftime('%d %b %Y, %I:%M %p')}")
    print()

    # ── Layer scores ─────────────────────────
    l1_score = l1["user_risk_score"]
    l2_score = l2["amount_risk_score"]
    l3_score = l3["receiver_risk_score"]

    print("  LAYER BREAKDOWN:")
    print(f"  L1  Relationship  [{_bar(l1_score)}] {l1_score:3d}/100  — {l1['familiarity'].upper()}, {l1['transaction_count']} past txn(s)")
    print(f"  L2  Amount        [{_bar(l2_score)}] {l2_score:3d}/100  — ratio {l2['ratio_to_avg30']:.2f}x avg (avg=₹{stats.get('avg_amount_overall',0):,.0f})")
    print(f"  L3  Receiver ML   [{_bar(l3_score)}] {l3_score:3d}/100  — fraud_flag_ratio={recv.get('fraud_flag_ratio',0):.2f}")
    print()

    # ── Final result ─────────────────────────
    fs = final["final_risk_score"]
    print(f"  FINAL RISK SCORE : " + color + BOLD + f"{fs}%" + RESET)
    print(f"  RISK LEVEL       : " + color + BOLD + f"{risk_level}" + RESET)
    print(f"  APP ACTION       : " + BOLD + ACTION_EMOJI.get(final['action'], final['action']) + RESET)
    print()

    # ── What to say to judges ─────────────────
    tell_judges(s, final, l1, l2, l3, stats, recv)
    print()


def tell_judges(s, final, l1, l2, l3, stats, recv):
    """Generate a script of what to say to judges before running live."""
    fs    = final["final_risk_score"]
    level = final["risk_level"]
    amt   = s["amount"]
    avg   = stats.get("avg_amount_overall", 0)
    ffr   = recv.get("fraud_flag_ratio", 0)
    txn_c = l1["transaction_count"]

    print("  " + BOLD + "📣  TELL THE JUDGES:" + RESET)

    if level == "LOW":
        print(f'  "This user regularly pays this contact — {txn_c} past transactions.')
        print(f'   Amount ₹{amt:,} is within their normal spending (avg ₹{avg:,.0f}).')
        print(f'   The system will flag this as LOW risk and ALLOW immediately."')

    elif level == "MODERATE":
        relation = f"{txn_c} past transaction(s)" if txn_c > 0 else "first time paying this receiver"
        print(f'  "This is the {relation}.')
        print(f'   The amount ₹{amt:,} is {l2["ratio_to_avg30"]:.1f}x their average (₹{avg:,.0f}).')
        print(f'   Receiver has a partial fraud history (flag ratio: {ffr:.0%}).')
        print(f'   The system flags this as MODERATE — the app shows a caution dialog.')
        print(f'   User must consciously confirm before proceeding."')

    elif level == "HIGH":
        print(f'  "The receiver has a fraud signal ratio of {ffr:.0%}.')
        print(f'   Amount ₹{amt:,} is {l2["ratio_to_avg30"]:.1f}x the user\'s average (₹{avg:,.0f}).')
        print(f'   Combined risk score is {fs}% — HIGH risk.')
        print(f'   The app prompts OTP + shows a strong warning. Receiver is flagged.')
        print(f'   User can still pay, but must consciously accept the risk."')

    elif level == "CRITICAL":
        print(f'  "All three layers fire simultaneously:')
        print(f'   — L3: Receiver fraud ratio = {ffr:.0%} (historical fraud receiver)')
        print(f'   — L2: Amount ₹{amt:,} is {l2["ratio_to_avg30"]:.1f}x the user\'s average (₹{avg:,.0f})')
        print(f'   — L1: Relationship score = {l1["user_risk_score"]} (unfamiliar receiver)')
        print(f'   Final score = {fs}% → CRITICAL.')
        print(f'   The system blocks the transaction and flags the receiver in the user\'s account."')


def print_summary(results):
    print(BOLD + "═" * 70 + RESET)
    print(BOLD + "   QUICK REFERENCE CARD  (share with team before demo)" + RESET)
    print(BOLD + "═" * 70 + RESET)
    print(f"  {'#':<4} {'Scenario':<38} {'Score':>6}  {'Level':<10} {'App Shows'}")
    print("  " + "─" * 66)
    for i, (s, r) in enumerate(results, 1):
        f     = r["final"]
        level = f["risk_level"]
        score = f["final_risk_score"]
        color = RISK_COLORS.get(level, "")
        action_map = {"ALLOW": "Pay button (green)", "WARN": "Caution dialog (amber)",
                      "OTP": "OTP + Risk warning (red)", "BLOCK": "BLOCK + flag receiver"}
        action_str = action_map.get(f["action"], f["action"])
        short_label = s["label"].split("—")[1].strip()[:36]
        print(f"  {i:<4} {short_label:<38} " + color + f"{score:>4}%" + RESET + f"  {color}{level:<10}{RESET} {action_str}")
    print(BOLD + "═" * 70 + RESET)
    print()
    print("  Run the same transaction in the app → same result. Go impress them! 🚀")
    print()


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Change cwd so relative CSV paths resolve correctly
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print_header()
    results = []
    for scenario in DEMO_SCENARIOS:
        try:
            result = run_scenario(scenario)
            results.append((scenario, result))
            print_scenario(scenario["label"], scenario, result)
        except Exception as e:
            print(f"\n  ❌ ERROR in '{scenario['label']}': {e}\n")
            import traceback; traceback.print_exc()

    if results:
        print_summary(results)
