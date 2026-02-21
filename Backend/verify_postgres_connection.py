import psycopg2
import time

dsn_localhost = "postgresql://postgres:sentra_secure_2026@localhost:5433/fraud_detection"
dsn_127 = "postgresql://postgres:sentra_secure_2026@127.0.0.1:5433/fraud_detection"

def verify(dsn):
    print(f"Attempting to connect to {dsn}...")
    try:
        conn = psycopg2.connect(dsn)
        print(f"SUCCESS: Connected to PostgreSQL on port 5433 using {dsn}!")
        conn.close()
        return True
    except Exception as e:
        print(f"FAILURE connect to {dsn}: {e}")
        return False

if __name__ == "__main__":
    time.sleep(2) # Wait for start
    if verify(dsn_localhost):
        pass
    elif verify(dsn_127):
        pass
    else:
        print("Both failed.")
