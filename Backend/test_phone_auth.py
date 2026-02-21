import requests
import random

BASE_URL = "http://localhost:8000/api"

def test_auth_flow():
    phone = f"99{random.randint(10000000, 99999999)}"
    
    # 1. Test Signup with Phone and UPI
    signup_data = {
        "full_name": "Test User",
        "phone": phone,
        "password": "SecurePassword123",
        "upi_id": f"testuser{phone}@okaxis"
    }
    
    print(f"Testing Signup for {phone}...")
    signup_res = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
    print(f"Signup Status: {signup_res.status_code}")
    if signup_res.status_code not in (200, 201):
        print(f"Signup Failed: {signup_res.text}")
        return False
    
    print("Signup Success:", signup_res.json().get('user_id'))
    print("UPI ID Stored:", signup_res.json().get('upi_id'))

    # 2. Test Login with Phone
    login_data = {
        "phone": phone,
        "password": "SecurePassword123"
    }
    
    print("\nTesting Login...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Login Status: {login_res.status_code}")
    if login_res.status_code != 200:
        print(f"Login Failed: {login_res.text}")
        return False
        
    print("Login Success for:", login_res.json().get('user_id'))
    print("UPI ID Returned:", login_res.json().get('upi_id'))
    return True

if __name__ == "__main__":
    test_auth_flow()
