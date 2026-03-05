from flask import Blueprint, request, jsonify, session
from services.user_service import user_service
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        # Validate input
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        # Validate email format
        if not validate_email(email):
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        # Validate password strength
        if len(password) < 6:
            return jsonify({
                'success': False,
                'error': 'Password must be at least 6 characters'
            }), 400
        
        # Create user
        user = user_service.create_user(email, password)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'An account with this email already exists'
            }), 409
        
        # Create session
        session.permanent = True
        session['user_id'] = str(user.id)
        session['email'] = user.email
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        # Validate input
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        # Verify credentials
        user = user_service.verify_user(email, password)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid email or password'
            }), 401
        
        # Create session
        session.permanent = True
        session['user_id'] = str(user.id)
        session['email'] = user.email
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout a user"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500


@auth_bp.route('/session', methods=['GET'])
def check_session():
    """Check if user has an active session"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'authenticated': False
            }), 401
        
        user = user_service.get_user_by_id(user_id)
        
        if not user:
            session.clear()
            return jsonify({
                'success': False,
                'authenticated': False
            }), 401
        
        return jsonify({
            'success': True,
            'authenticated': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500
