import json
from app.core.risk_orchestrator import orchestrator
from app.database.connection import init_db, SessionLocal
from app.database.models import User

txn = {
    "receiver": "recv3@upi",
    "amount": 1000,
    "device_id": "device-unknown",
    "note": "user11 pays recv3 1000"
}
user_id = "user11@upi"

def ensure_user_exists(user_id: str):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.user_id == user_id).first()
        if not u:
            u = User(user_id=user_id, email=f"{user_id.replace('@','_')}@example.com", full_name="User Eleven")
            db.add(u)
            db.commit()
    finally:
        db.close()

if __name__ == '__main__':
    init_db()
    ensure_user_exists(user_id)
    out = orchestrator.analyze_transaction(txn, user_id, db=None, save=False)
    print(json.dumps(out, indent=2, default=str))
