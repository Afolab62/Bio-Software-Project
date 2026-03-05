from typing import Optional
from sqlalchemy.exc import IntegrityError
from models.user import User
from database import get_db


class UserService:
    """Service for managing users with PostgreSQL storage"""
    
    def create_user(self, email: str, password: str) -> Optional[User]:
        """Create a new user"""
        db = get_db()
        try:
            # Check if user exists
            existing_user = db.query(User).filter(User.email == email.lower()).first()
            if existing_user:
                return None
            
            # Create user
            password_hash = User.hash_password(password)
            user = User(email=email.lower(), password_hash=password_hash)
            
            # Save to database
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return user
        except IntegrityError:
            db.rollback()
            return None
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        db = get_db()
        try:
            user = db.query(User).filter(User.email == email.lower()).first()
            return user
        finally:
            db.close()
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        db = get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user
        finally:
            db.close()
    
    def verify_user(self, email: str, password: str) -> Optional[User]:
        """Verify user credentials"""
        user = self.get_user_by_email(email)
        if user and User.verify_password(password, user.password_hash):
            return user
        return None


# Global instance
user_service = UserService()
