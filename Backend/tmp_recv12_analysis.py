import json
from app.core.risk_orchestrator import orchestrator
from app.core.context_engine import get_user_context
from app.database.connection import init_db, SessionLocal
from app.database.models import User

user_id = "user11@upi"
receiver = "recv12@upi"

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
        recv_info = context.receiver_info
        recv_score = orchestrator._calculate_receiver_score(context, receiver)
        out = {
            'receiver': receiver,
            'receiver_info': recv_info,
            'receiver_score': recv_score
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()
