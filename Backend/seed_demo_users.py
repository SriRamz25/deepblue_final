import asyncio
from app.database.connection import engine
from app.database.models import Base
from app.services.auth_service import create_user
from app.models.auth import SignupRequest

async def seed_demo_users():
    # 1. Ensure the DB schemas are ready
    Base.metadata.create_all(bind=engine)
    print("Database tables ensured.")

    # 2. Map of synthetic users
    demo_users = [
        SignupRequest(full_name="User One", phone="9911111111", password="password123", email="user1@example.com", upi_id="user1@upi"),
        SignupRequest(full_name="User Two", phone="9922222222", password="password123", email="user2@example.com", upi_id="user2@upi"),
        SignupRequest(full_name="User Three", phone="9933333333", password="password123", email="user3@example.com", upi_id="user3@upi"),
        SignupRequest(full_name="User Four", phone="9944444444", password="password123", email="user4@example.com", upi_id="user4@upi"),
        SignupRequest(full_name="User Five", phone="9955555555", password="password123", email="user5@example.com", upi_id="user5@upi"),
    ]

    print(f"Attempting to seed {len(demo_users)} demo users...")
    
    for user_req in demo_users:
        try:
            # We use the existing auth service to securely hash passwords & handle conflicts
            user = create_user(user_req)
            print(f"Successfully seeded: {user.full_name} | Phone: {user.phone} | UPI: {user.upi_id}")
        except Exception as e:
            print(f"Skipping {user_req.full_name}: {e}")

if __name__ == "__main__":
    asyncio.run(seed_demo_users())
