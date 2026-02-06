import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv('DATABASE_URL', '')
print(f"Original: {db_url}")

if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
print(f"Modified: {db_url}")
