"""Security utilities for FuelLens application."""

from functools import wraps
from flask import request, abort, current_app
from flask_login import current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import bcrypt


# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# Encryption for sensitive data
def get_cipher():
    """Get Fernet cipher for encryption/decryption."""
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY not configured")
    return Fernet(key.encode() if isinstance(key, str) else key)


def hash_password(password):
    """Hash a password for storage."""
    return pwd_context.hash(password)


def verify_password(password, hashed):
    """Verify a stored password against plain text."""
    return pwd_context.verify(password, hashed)


def validate_password_strength(password):
    """Validate password strength requirements."""
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"


def encrypt_data(data):
    """Encrypt sensitive data."""
    cipher = get_cipher()
    return cipher.encrypt(data.encode())


def decrypt_data(encrypted_data):
    """Decrypt sensitive data."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted_data).decode()


def role_required(*roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if current_user.role not in roles:
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_vehicle_number(vehicle_number):
    """Validate Indian vehicle number plate format."""
    # Indian vehicle number format: XX[0-9][0-9][A-Z]{1,2}[0-9]{1,4}
    # Examples: KA01AB1234, MH02GZ4567, DL4C1234, RJ09CB1234
    pattern = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}$'
    return re.match(pattern, vehicle_number.upper()) is not None


def sanitize_input(input_string):
    """Basic input sanitization to prevent XSS."""
    if not input_string:
        return input_string
    
    # Remove potentially dangerous characters/sequences
    sanitized = input_string.replace('<', '&lt;').replace('>', '&gt;')
    sanitized = sanitized.replace('"', '&quot;').replace("'", '&#x27;')
    sanitized = sanitized.replace('/', '&#x2F;')
    
    return sanitized


def rate_limit_exempt():
    """Decorator to exempt endpoints from rate limiting."""
    def decorator(f):
        f._rate_limit_exempt = True
        return f
    return decorator


# Global limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


def apply_rate_limits():
    """Apply rate limits to the application."""
    # Apply default limits to all routes except exempted ones
    pass