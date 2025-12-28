"""Development configuration for FuelLens application."""

from .base import Config
import os


class DevelopmentConfig(Config):
    """Development configuration."""
    
    # Debug mode
    DEBUG = True
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'postgresql://fuellens_dev:password@localhost/fuellens_dev'
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-for-development'
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    
    # Mail
    MAIL_SUPPRESS_SEND = True  # Don't actually send emails in development
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    
    # Rate limiting
    RATELIMIT_ENABLED = False  # Disable rate limiting in development