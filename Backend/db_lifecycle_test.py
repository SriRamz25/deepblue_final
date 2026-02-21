import asyncio
from app.database.connection import SessionLocal
from app.database.models import User
from app.services.auth_service import create_user, authenticate_user
from app.models.auth import SignupRequest, LoginRequest
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_db_user_directly(phone: str, upi_id: str):
    """Query the DB directly via SQLAlchemy to verify row insertion."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            print(f"❌ [DB Check] User with phone {phone} NOT FOUND in database!")
            return False
            
        print(f"✅ [DB Check] User found! DB ID: {user.user_id}")
        print(f"   ► Stored Phone: {user.phone}")
        print(f"   ► Stored UPI: {user.upi_id}")
        print(f"   ► Password Hash exists? {'Yes' if user.password_hash else 'No'}")
        
        if user.upi_id != upi_id:
            print(f"❌ [DB Check] UPI ID Mismatch! Expected {upi_id}, got {user.upi_id}")
            return False
            
        return True
    finally:
        db.close()

async def interactive_test():
    print("===============================================")
    print("   SENTRAPAY DB PERSISTENCE & LOGIN TESTER")
    print("===============================================")
    
    # 1. Input Dummy Values
    test_phone = "9876543210"
    test_password = "SecurePassword123"
    test_upi_id = "testuser@upi"
    
    # Define Signup Request
    signup_req = SignupRequest(
        full_name="End To End Tester",
        phone=test_phone,
        password=test_password,
        email="optional_email@example.com",
        upi_id=test_upi_id
    )

    # 2. STEP 1: Execute Creation
    print("\n[STEP 1] Creating User via AuthService...")
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.phone == test_phone).first()
        if existing_user:
            print(f"User {test_phone} already exists, skipping creation.")
        else:
            created_user = create_user(db, signup_req)
            print(f"✅ Success! API returned User ID: {created_user.user_id}")
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        db.close()
        return

    # 3. Verify exactly how it is stored in DB
    print("\n[STEP 2] Verifying actual Row data in SQLite DB...")
    db_ok = verify_db_user_directly(test_phone, test_upi_id)
    if not db_ok:
        return

    # 4. STEP 3: Execute Sign-In
    print("\n[STEP 3] Testing Login using Phone + Password...")
    login_req = LoginRequest(phone=test_phone, password=test_password)
    try:
        logged_in_user = authenticate_user(db, login_req)
        
        if logged_in_user:
            print("✅ LOGIN SUCCESS! Credentials perfectly matched.")
            print(f"   ► Welcome back, {logged_in_user.full_name}!")
        else:
            print("❌ LOGIN FAILED! Got None from authentication logic.")
            
    except Exception as e:
        print(f"❌ LOGIN FAILED OUTRIGHT: Exception thrown -> {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(interactive_test())
