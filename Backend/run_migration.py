import os
import psycopg2
from dotenv import load_dotenv

# Load .env
load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("[ERROR] DATABASE_URL not found in .env")
    exit(1)

print("Connecting to database...")
try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Check current tables
    tables = ['bus_bookings', 'flight_bookings', 'train_bookings']
    for table in tables:
        print(f"Altering table {table} to add selected_seats...")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS selected_seats VARCHAR(255);")
        
        # Verify columns
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table}' AND column_name = 'selected_seats';
        """)
        col = cur.fetchone()
        if col:
            print(f"[SUCCESS] {table}.selected_seats added successfully (type: {col[1]})")
        else:
            print(f"[ERROR] Failed to add selected_seats to {table}")

    conn.close()
    print("[SUCCESS] Migrations completed successfully!")
except Exception as e:
    print(f"[ERROR] Error running migration: {e}")
