from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from config import Config

_db_url = Config.SQLALCHEMY_DATABASE_URI
_is_sqlite = _db_url.startswith('sqlite')

# SQLite needs check_same_thread=False for Flask's threaded requests.
# Postgres gets a connection timeout instead.
_connect_args = {"check_same_thread": False} if _is_sqlite else {"connect_timeout": 10}

# SQLite doesn't support pool_pre_ping or pool_recycle the same way
_engine_kwargs = dict(
    echo=False,
    connect_args=_connect_args,
)
if not _is_sqlite:
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_recycle"] = 3600

engine = create_engine(_db_url, **_engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create scoped session for thread-safe access
db = scoped_session(SessionLocal)

# Create base class for models
Base = declarative_base()

def get_db():
    """Get database session"""
    return db

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
