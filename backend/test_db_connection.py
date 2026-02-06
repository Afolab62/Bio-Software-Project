import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

db_url = os.getenv('DATABASE_URL')
print(f"Testing connection to: {db_url[:20]}...{db_url[-20:]}")

try:
    # Test connection
    conn = psycopg.connect(db_url, connect_timeout=10)
    print("✓ Connection successful!")
    
    # Test query
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✓ PostgreSQL version: {version[0][:50]}...")
    
    cursor.close()
    conn.close()
    print("✓ Connection closed successfully")
    
except Exception as e:
    print(f"✗ Connection failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
