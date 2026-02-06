from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import Config

# Create database engine with connection pooling and timeout settings
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI, 
    echo=False,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,   # Recycle connections after 1 hour
    connect_args={
        "connect_timeout": 10,  # 10 second connection timeout
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
