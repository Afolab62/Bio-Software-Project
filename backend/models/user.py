from datetime import datetime
from typing import Optional
import bcrypt
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid


class User(Base):
    """User model for authentication"""
    __tablename__ = 'users'
    
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
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against a hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
