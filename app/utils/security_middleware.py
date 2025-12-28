"""Security middleware for FuelLens application."""

from functools import wraps
from flask import request, jsonify, current_app, session
from flask_login import current_user
from app.models import User
from app import limiter
import time
import ipaddress
from datetime import datetime


class SecurityMiddleware:
    """Security middleware class containing various security functions."""
    
    @staticmethod
    def check_ip_reputation(ip_addr):
        """Check if IP address is in any known threat lists."""
        # This would typically integrate with threat intelligence services
        # For now, we'll just return True (IP is OK)
        # In production, this could check against lists like Spamhaus, TOR exit nodes, etc.
        return True
    
    @staticmethod
    def log_security_event(event_type, user_id=None, ip_address=None, details=None):
        """Log security-related events."""
        from app import db
        from app.models import SecurityLog  # Assuming we have a security log model
        
        # Create security log entry
        security_log = SecurityLog(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address or request.remote_addr,
            details=details,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(security_log)
        db.session.commit()
    
    @staticmethod
    def check_rate_limit():
        """Check rate limiting for the current request."""
        # This is handled by Flask-Limiter, but we can add custom logic here
        pass
    
    @staticmethod
    def validate_request_headers():
        """Validate common security headers."""
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        }
        
        # Check for suspicious headers that might indicate attacks
        suspicious_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'CF-Connecting-IP'
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                # Log potential header injection attempt
                SecurityMiddleware.log_security_event(
                    'HEADER_INJECTION_ATTEMPT',
                    user_id=current_user.id if current_user.is_authenticated else None,
                    ip_address=request.remote_addr,
                    details=f"Suspicious header: {header}"
                )
    
    @staticmethod
    def check_user_session_security():
        """Check if user session is secure."""
        if current_user.is_authenticated:
            # Check if user account is locked
            if current_user.is_account_locked():
                from flask_login import logout_user
                logout_user()
                return False, "Account is locked due to multiple failed login attempts"
            
            # Check if user is active
            if not current_user.is_active:
                from flask_login import logout_user
                logout_user()
                return False, "Account is inactive"
        
        return True, "Session is secure"
    
    @staticmethod
    def sanitize_request_data(data):
        """Sanitize request data to prevent injection attacks."""
        from app.utils.helpers import sanitize_input
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if isinstance(value, str):
                    sanitized[key] = sanitize_input(value)
                elif isinstance(value, dict):
                    sanitized[key] = SecurityMiddleware.sanitize_request_data(value)
                elif isinstance(value, list):
                    sanitized[key] = [SecurityMiddleware.sanitize_request_data(item) if isinstance(item, (dict, str)) else item for item in value]
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, str):
            return sanitize_input(data)
        else:
            return data


def security_check(f):
    """Decorator to apply security checks to routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if IP is reputable
        if not SecurityMiddleware.check_ip_reputation(request.remote_addr):
            return jsonify({'error': 'IP address blocked for security reasons'}), 403
        
        # Validate request headers
        SecurityMiddleware.validate_request_headers()
        
        # Check user session security
        is_secure, message = SecurityMiddleware.check_user_session_security()
        if not is_secure:
            return jsonify({'error': message}), 401
        
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_exempt(f):
    """Decorator to exempt endpoints from rate limiting."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Mark this function as exempt from rate limiting
        request._rate_limit_exempt = True
        return f(*args, **kwargs)
    return decorated_function


# Rate limiting decorators
login_rate_limit = limiter.limit("5 per minute", per_method=True, methods=['POST'])
general_rate_limit = limiter.limit("100 per hour; 1000 per day")
api_rate_limit = limiter.limit("10 per minute; 100 per hour")