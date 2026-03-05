from datetime import datetime
from typing import Optional
import bcrypt
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid


class User(Base):
    """
    Stores registered user accounts.
    Passwords are never stored in plaintext — only a bcrypt hash is persisted.
    Authentication is handled by verifying submitted passwords against the hash.
    """
    __tablename__ = 'users'
    
    # UUID primary key — avoids sequential integer IDs being guessable in API routes

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert user to dictionary (excluding password)"""
        return {
            'id': str(self.id),
            'email': self.email,
            'createdAt': self.created_at.isoformat()
        }
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plaintext password using bcrypt before storing in the database.
        bcrypt automatically generates and embeds a random salt - two
        identical passwords will produce different hashes.
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a plaintext password against a stored bcrypt hash at login.
        bcrypt.checkpw handles extracting emdbed from hash
        """
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
