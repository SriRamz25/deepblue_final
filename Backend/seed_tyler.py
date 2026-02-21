
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import User, ReceiverReputation
from app.utils.security import hash_password
import uuid

def seed_tyler():
    db = SessionLocal()
    try:
        # User details
        name = "Tyler Durden"
        phone = "9876543210"
        email = f"{phone}@sentra.app"
        upi_id = "tylerdurden@oksbi"
        pin = "1234" # Default PIN
        
        # Check if user exists
        existing_user = db.query(User).filter(User.phone == phone).first()
        if not existing_user:
            print(f"Creating user: {name}")
            new_user = User(
                email=email,
                phone=phone,
                password_hash=hash_password(pin),
                full_name=name,
                trust_score=95.0, # Trusted by default
                risk_tier="GOLD",
                known_devices=["DEV-TYLER-001"]
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            print(f"User created with ID: {new_user.user_id}")
        else:
            print(f"User {name} already exists.")

        # Also add to Receiver Reputation so the UPI ID can be validated
        existing_rep = db.query(ReceiverReputation).filter(ReceiverReputation.receiver == upi_id).first()
        if not existing_rep:
            print(f"Registering VPA reputation: {upi_id}")
            new_rep = ReceiverReputation(
                receiver=upi_id,
                total_transactions=150,
                successful_transactions=148,
                reputation_score=0.98, # High trust
            )
            db.add(new_rep)
            db.commit()
            print(f"VPA registered.")
        else:
            print(f"VPA {upi_id} already registered.")

        print("\n✅ Seed completed successfully.")
        print(f"Login details:\nPhone/Email: {phone}\nPIN: {pin}")

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_tyler()
