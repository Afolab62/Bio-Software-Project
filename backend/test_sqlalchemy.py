from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

db_url = os.getenv('DATABASE_URL', '')
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)

print(f"Testing SQLAlchemy with: {db_url[:30]}...{db_url[-30:]}")

try:
    engine = create_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "connect_timeout": 10,
        }
    )
    
    print("✓ Engine created")
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"✓ Connection successful! Result: {result.scalar()}")
    
    print("✓ SQLAlchemy connection works!")
    
except Exception as e:
    print(f"✗ SQLAlchemy connection failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
