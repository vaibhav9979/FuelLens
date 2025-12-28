"""Testing configuration for FuelLens application."""

from .base import Config
import os


class TestingConfig(Config):
    """Testing configuration."""
    
    # Debug mode
    DEBUG = True
    TESTING = True
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'postgresql://fuellens_test:password@localhost/fuellens_test'
    
    # Security
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing
    
    # Mail
    MAIL_SUPPRESS_SEND = True
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    
    # Rate limiting
    RATELIMIT_ENABLED = False
    
    # Session
    SESSION_COOKIE_SECURE = False