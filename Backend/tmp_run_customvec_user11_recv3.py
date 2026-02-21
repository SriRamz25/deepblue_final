import json
from app.core.context_engine import get_user_context
from app.core.ml_engine import build_custom_vector, predict_with_custom_vector
from app.database.connection import init_db, SessionLocal
from app.database.models import User

user_id = "user11@upi"
receiver = "recv3@upi"

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
    db = SessionLocal()
    try:
        context = get_user_context(user_id, receiver, db)
        txn = {"amount": 1000, "receiver": receiver, "device_id": "device-unknown"}
        vec = build_custom_vector(txn, context)
        ml = predict_with_custom_vector(txn, context)
        print(json.dumps({"custom_vector": vec, "ml_score": ml.ml_score, "model_version": ml.model_version}, indent=2))
    finally:
        db.close()
