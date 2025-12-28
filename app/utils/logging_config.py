"""Logging configuration for FuelLens application."""

import logging
import logging.config
import os
from pythonjsonlogger import jsonlogger


def setup_logging(log_level='INFO'):
    """Set up logging configuration for the application."""
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Define log format
    log_format = '%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(user_id)s'
    
    # Configure logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s %(funcName)s %(lineno)d: %(message)s'
            },
            'json': {
                '()': jsonlogger.JsonFormatter,
                'format': log_format
            }
        },
        'handlers': {
            'default': {
                'level': log_level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'level': log_level,
                'formatter': 'detailed',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            },
            'security_file': {
                'level': 'INFO',
                'formatter': 'json',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/security.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            },
            'error_file': {
                'level': 'ERROR',
                'formatter': 'detailed',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/error.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['default', 'file'],
                'level': log_level,
                'propagate': False
            },
            'app.security': {
                'handlers': ['security_file'],
                'level': 'INFO',
                'propagate': False
            },
            'app.errors': {
                'handlers': ['error_file', 'default'],
                'level': 'ERROR',
                'propagate': False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # Set specific log levels for third-party libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name):
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


# Context filter to add request and user context to logs
class ContextFilter(logging.Filter):
    """Logging filter to add request and user context."""
    
    def filter(self, record):
        # These will be set by the application context
        record.request_id = getattr(self, 'request_id', 'unknown')
        record.user_id = getattr(self, 'user_id', 'anonymous')
        record.endpoint = getattr(self, 'endpoint', 'unknown')
        return True


def log_security_event(event_type, user_id=None, ip_address=None, details=None):
    """Log a security-related event."""
    logger = get_logger('app.security')
    logger.info(
        "Security event",
        extra={
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details
        }
    )