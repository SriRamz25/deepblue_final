"""
Demo Test Cases — Run all 4 scenarios to see exact scores.
Usage: python demo_test_cases.py
"""
import sys
sys.path.insert(0, '.')

from app.core.data_loader import load_sender_history, get_sender_stats, get_receiver_profile
from app.core.relationship_engine import analyze_user_relationship
from app.core.amount_risk_engine import analyze_amount_risk
from app.core.receiver_ml_engine import analyze_receiver_risk
from app.core.final_risk_engine import compute_final_risk


def run_scenario(label, sender, receiver, amount, timestamp):
    df = load_sender_history()
    l1 = analyze_user_relationship(sender, receiver, df)
    stats = get_sender_stats(sender)
    l2 = analyze_amount_risk(amount, stats)
    rp = get_receiver_profile(receiver)
    ctx = dict(stats)
    ctx['impossible_travel_count'] = rp.get('impossible_travel_count', 0)
    ctx['location_mismatch'] = rp.get('location_mismatches', 0)
    txn = {'amount': amount, 'receiver': receiver, 'timestamp': timestamp}
    l3 = analyze_receiver_risk(txn, ctx, None)
    final = compute_final_risk(l1['user_risk_score'], l2['amount_risk_score'], l3['receiver_risk_score'])

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  {sender} -> {receiver}, Rs.{amount:,} at {timestamp[11:16]}")
    print(f"{'='*60}")
    print(f"  Layer 1 (Relationship): {l1['user_risk_score']}/100  [{l1['familiarity']}]  ({l1['transaction_count']} past txns)")
    print(f"  Layer 2 (Amount Risk):  {l2['amount_risk_score']}/100  [{l2['risk_level']}]")
    print(f"  Layer 3 (Receiver ML):  {l3['receiver_risk_score']}/100  [{l3['risk_level']}]")
    print(f"    -> impossible_travel: {rp.get('impossible_travel_count', 0)} events")
    if rp.get('impossible_travel_events'):
        for ev in rp['impossible_travel_events']:
            print(f"      {ev['from_city']} -> {ev['to_city']} in {ev['time_gap_min']}min ({ev['distance_km']}km)")
    print(f"  ----------------------------------------")
    print(f"  FINAL SCORE: {final['final_risk_score']}%  ->  {final['action']}  ({final['risk_level']})")
    return final


if __name__ == '__main__':
    # TEST 1: BLOCK — trusted sender, but FRAUD receiver + huge amount + 2AM
    run_scenario(
        "TEST 1: SHOULD BLOCK",
        "user3@upi", "recv9@upi", 50000, "2026-02-20T02:00:00"
    )

    # TEST 2: ALLOW — trusted sender + safe receiver + normal amount + daytime
    run_scenario(
        "TEST 2: SHOULD ALLOW",
        "user1@upi", "recv1@upi", 3000, "2026-02-20T14:00:00"
    )

    # TEST 3: OTP/WARN — first-time to FRAUD receiver + normal amount
    run_scenario(
        "TEST 3: FIRST TIME TO FRAUD RECEIVER",
        "user1@upi", "recv8@upi", 3000, "2026-02-20T14:00:00"
    )

    # TEST 4: ALLOW — high-value sender, trusted receiver, normal for them
    run_scenario(
        "TEST 4: HIGH-VALUE BUT NORMAL",
        "user10@upi", "recv17@upi", 35000, "2026-02-20T11:00:00"
    )
