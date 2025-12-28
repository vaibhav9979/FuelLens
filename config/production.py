"""Production configuration for FuelLens application."""

from .base import Config
import os


class ProductionConfig(Config):
    """Production configuration."""
    
    # Debug mode
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://fuellens:password@localhost/fuellens'
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    
    # Session management
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Mail
    MAIL_SUPPRESS_SEND = False
    
    # Logging
    LOG_LEVEL = 'WARNING'
    
    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/1')
    
    # Security
    WTF_CSRF_SSL_STRICT = True
    
    # Performance
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files