import sys
from app.database.connection import SessionLocal
from app.database.models import User

def check_user():
    db = SessionLocal()
    with open("my_output.txt", "w") as f:
        try:
            user = db.query(User).filter(User.phone == "1234567890").first()
            if user:
                f.write(f"User EXISTS! Phone: {user.phone}, UPI: {user.upi_id}\n")
            else:
                f.write("User does not exist with that phone number.\n")
        except Exception as e:
            f.write(f"Exception: {e}\n")
    db.close()

if __name__ == "__main__":
    check_user()
