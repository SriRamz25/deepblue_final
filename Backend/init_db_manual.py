import sys
import os

# Add parent directory to path to allow importing app modules
sys.path.append(os.getcwd())

from app.database.connection import engine
from app.database import models

def init():
    print("⏳ Initializing database tables...")
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    init()
