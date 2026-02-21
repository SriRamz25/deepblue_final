"""
Live Test Cases for user4@upi — 3-Layer Risk Orchestrator
Run: python run_test_cases.py
"""
import sys, os
sys.path.insert(0, ".")
import requests

BASE = "http://localhost:8000"

# ── Login ─────────────────────────────────────────────────────────────────────
resp = requests.post(f"{BASE}/api/auth/login", json={"phone": "9876543210", "password": "password123"})
if resp.status_code != 200:
    print(f"Login failed: {resp.text}"); sys.exit(1)

login = resp.json()
TOKEN = login["token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print(f"Logged in as: {login['upi_id']} ({login['user_id']})")
print("=" * 72)

# Thresholds (from final_risk_engine.py):
#   ALLOW  < 25%   WARN  25-44%   OTP  45-69%   BLOCK >= 70%
#
# user4@upi — avg=Rs.8,100 | known receivers: recv13,14,15,16
# Receiver CSV fraud profiles:
#   recv1,13 = 0% flagged (clean)      recv5 = 50% flagged (risky)
#   recv6,7,8,9,10 = 100% flagged      recv17,18,19,20 = 100% flagged (new)
TEST_CASES = [
    # Layer 1 tests — familiarity with sender CSV
    ("TC1", "Known recv13 + normal amt (L1=0)          => ALLOW", "recv13@upi",  8_000,   "ALLOW"),
    ("TC2", "Stranger recv1 + normal amt (L1=50)       => ALLOW", "recv1@upi",   8_000,   "ALLOW"),

    # Layer 2 tests — amount deviation
    ("TC3", "Known recv13 + 25x normal (L2=50)         => WARN ", "recv13@upi",  200_000, "WARN"),

    # Layer 3 tests — receiver fraud signal
    ("TC4", "recv1 clean recv + normal amt (L3=0)      => ALLOW", "recv1@upi",   8_000,   "ALLOW"),
    ("TC5", "recv6 100%fraud + normal amt (L3=80)      => WARN ", "recv6@upi",   8_000,   "WARN"),
    ("TC6", "recv10 100%fraud + 10x amt (L3=100)       => WARN ", "recv10@upi",  80_000,  "WARN"),

    # Full pipeline — all 3 layers together
    ("TC7", "Known+clean+normal  (L1=0,L2=5,L3=0)     => ALLOW", "recv13@upi",  8_000,   "ALLOW"),
    ("TC8", "Stranger+fraud+high (L1=50,L2=40,L3=100) => WARN ", "recv6@upi",   50_000,  "WARN"),
]

passed = 0
for tc, desc, recv, amt, expected in TEST_CASES:
    payload = {
        "receiver":   recv,
        "amount":     amt,
        "note":       "test payment",
        "sender_upi": "user4@upi",
        "device_id":  "dev4",
    }
    r = requests.post(f"{BASE}/api/payment/intent", json=payload, headers=HEADERS)

    if r.status_code != 200:
        print(f"[{tc}] ❌  HTTP {r.status_code}: {r.text[:100]}")
        print()
        continue

    data   = r.json()
    action = data.get("action", "?")
    score  = data.get("risk_percentage", 0)
    level  = data.get("risk_level", "?")
    debug  = data.get("debug", {})
    fd     = debug.get("final_decision", {})
    c      = fd.get("components", {})
    l1 = debug.get("layer1_relationship", {}).get("user_risk_score", 0)
    l2 = debug.get("layer2_amount", {}).get("amount_risk_score", 0)
    l3 = debug.get("layer3_receiver", {}).get("receiver_risk_score", 0)

    ok = "✅" if action == expected.strip() else "⚠️ "
    if action == expected.strip():
        passed += 1

    print(f"[{tc}] {ok}  {desc}")
    print(f"       Receiver={recv:<16}  Amount=Rs.{amt:>8,}")
    print(f"       ACTION={action:<6}  SCORE={score}%  LEVEL={level}")
    print(f"       L1(Relationship)={l1}  L2(Amount)={l2}  L3(ReceiverML)={l3}")
    print()

print("=" * 72)
print(f"Results: {passed}/{len(TEST_CASES)} tests matched expected action")
