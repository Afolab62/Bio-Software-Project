import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration
    # Convert postgresql:// to postgresql+psycopg:// for psycopg3
    db_url = os.getenv('DATABASE_URL', '')
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration - 24 hour duration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS configuration
    CORS_ORIGINS = [os.getenv('FRONTEND_URL', 'http://localhost:3000')]
    CORS_SUPPORTS_CREDENTIALS = True
