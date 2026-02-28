"""
Auth routes: login/register placeholders (to be implemented).
"""
from flask import Blueprint
from app.extensions import login_manager

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    """Placeholder user loader — no User model yet."""
    return None


@auth_bp.get("/login")
def login():
    """Placeholder login route."""
    return "Login page placeholder"
