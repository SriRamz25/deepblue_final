"""
fix_db.py — PostgreSQL Schema Migration Utility for SentraPay
Adds missing columns to the transactions table and ensures all tables exist.
Uses SQLAlchemy against the PostgreSQL database defined in .env
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.database.connection import engine
from app.database import models

# ── 1. Ensure all tables exist ─────────────────────────────────────────────
print("🔄 Ensuring all tables exist in PostgreSQL...")
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ Tables created / verified.")
except Exception as e:
    print(f"❌ Failed to create tables: {e}")
    sys.exit(1)

# ── 2. Add any missing columns to transactions ─────────────────────────────
missing_columns = [
    ("payment_timestamp", "TIMESTAMP WITH TIME ZONE"),
    ("utr_number",        "VARCHAR(20)"),
    ("psp_name",          "VARCHAR(50)"),
    ("payment_method",    "VARCHAR(255)"),
    ("current_hash",      "VARCHAR(64)"),
    ("previous_hash",     "VARCHAR(64)"),
    ("completed_at",      "TIMESTAMP WITH TIME ZONE"),
    ("device_id",         "VARCHAR(100)"),
]

inspector = inspect(engine)
existing_cols = {col["name"] for col in inspector.get_columns("transactions")}
print(f"\nExisting columns in 'transactions': {sorted(existing_cols)}")

with engine.begin() as conn:
    for col_name, col_type in missing_columns:
        if col_name not in existing_cols:
            print(f"➕ Adding column '{col_name}' ({col_type})...")
            try:
                conn.execute(text(f'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS "{col_name}" {col_type}'))
                print(f"   ✅ Added '{col_name}'")
            except Exception as e:
                print(f"   ❌ Failed to add '{col_name}': {e}")
        else:
            print(f"   ✓  '{col_name}' already exists, skipping.")

print("\n✅ Database schema update complete.")
