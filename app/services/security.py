"""Security service for FuelLens application."""

from datetime import datetime, timedelta
from app.models import User
from app.utils.security import hash_password, verify_password, validate_password_strength
from app import db
import secrets
import string


class SecurityService:
    """Security service handling authentication and authorization."""
    
    @staticmethod
    def create_secure_password(length=16):
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def validate_and_hash_password(password):
        """Validate password strength and hash it."""
        is_valid, message = validate_password_strength(password)
        if not is_valid:
            return False, message
        
        hashed_password = hash_password(password)
        return True, hashed_password
    
    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user with email and password."""
        user = User.query.filter_by(email=email, is_active=True).first()
        
        if user and verify_password(password, user.password_hash):
            return user
        return None
    
    @staticmethod
    def reset_user_password(user, new_password):
        """Reset user password with validation."""
        is_valid, result = SecurityService.validate_and_hash_password(new_password)
        if not is_valid:
            return False, result
        
        user.password_hash = result
        user.password_reset_at = datetime.utcnow()
        db.session.commit()
        return True, "Password reset successfully"
    
    @staticmethod
    def generate_reset_token():
        """Generate a secure password reset token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_reset_token(token, max_age=3600):  # 1 hour
        """Validate password reset token."""
        # In a real implementation, you would check the token against a database
        # This is a simplified version
        if not token:
            return False
        return True