import asyncio
from app.database.connection import engine, SessionLocal
from app.database.models import Base
from app.services.auth_service import create_user
from app.models.auth import SignupRequest

async def seed_specific_user():
    Base.metadata.create_all(bind=engine)
    user_req = SignupRequest(
        full_name="User Four", 
        phone="1234567890", 
        password="Hello@123", 
        email="user4@example.com", 
        upi_id="user4@upi"
    )

    db = SessionLocal()
    try:
        user = create_user(db, user_req)
        print(f"Successfully seeded: {user.full_name} | Phone: {user.phone} | UPI: {user.upi_id}")
    except Exception as e:
        print(f"Failed to seed user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(seed_specific_user())
