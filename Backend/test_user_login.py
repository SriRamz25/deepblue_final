import sys
from app.database.connection import SessionLocal
from app.services.auth_service import authenticate_user
from app.models.auth import LoginRequest

def test_login():
    db = SessionLocal()
    with open("my_output.txt", "w") as f:
        req = LoginRequest(phone="1234567890", password="Hello@123")
        try:
            user = authenticate_user(db, req)
            f.write(f"Login Success: {user.phone}, {user.upi_id}\n")
        except Exception as e:
            f.write(f"Login Failed: {e}\n")
            if hasattr(e, 'detail'):
                f.write(f"Detail: {e.detail}\n")
    db.close()

if __name__ == "__main__":
    test_login()
