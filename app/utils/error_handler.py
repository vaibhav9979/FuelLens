"""Error handling and custom exception classes for FuelLens application."""

from flask import jsonify, request, current_app, render_template
from werkzeug.exceptions import HTTPException
from app.utils.logging_config import get_logger
from app.models import SecurityLog
import traceback
import sys
from functools import wraps


# Custom exception classes
class FuelLensException(Exception):
    """Base exception class for FuelLens application."""
    pass


class AuthenticationError(FuelLensException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(FuelLensException):
    """Raised when authorization fails."""
    pass


class ValidationError(FuelLensException):
    """Raised when validation fails."""
    pass


class DatabaseError(FuelLensException):
    """Raised when database operations fail."""
    pass


class OCRProcessingError(FuelLensException):
    """Raised when OCR processing fails."""
    pass


class SecurityError(FuelLensException):
    """Raised when security-related issues occur."""
    pass


# Logger for error handling
logger = get_logger('app.errors')


def init_error_handlers(app):
    """Initialize error handlers for the Flask application."""
    
    @app.errorhandler(400)
    def bad_request(error):
        logger.error(f"Bad request: {request.url} - {str(error)}")
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning(f"Unauthorized access attempt: {request.url}")
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        logger.warning(f"Forbidden access attempt: {request.url}")
        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        logger.info(f"Page not found: {request.url}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found'
            }), 404
        else:
            return render_template('errors/404.html'), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for this endpoint'
        }), 405
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        logger.warning(f"Rate limit exceeded: {request.url} from {request.remote_addr}")
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests. Please try again later.'
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {request.url} - {str(error)}", exc_info=True)
        
        # Log security event for 500 errors
        SecurityLog.log_event(
            event_type='INTERNAL_ERROR',
            ip_address=request.remote_addr,
            details=f"Error: {str(error)}\nTraceback: {traceback.format_exc()}"
        )
        
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        else:
            return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        # Log the error
        logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
        
        # Log security event for unhandled exceptions
        SecurityLog.log_event(
            event_type='UNHANDLED_EXCEPTION',
            ip_address=request.remote_addr,
            details=f"Error: {str(error)}\nTraceback: {traceback.format_exc()}",
            severity='high'
        )
        
        # Return JSON response for API endpoints
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        
        # Return HTML response for regular endpoints
        return render_template('errors/500.html'), 500


def handle_error_response(error, status_code=500):
    """Helper function to create standardized error responses."""
    logger.error(f"Error response: {str(error)}", exc_info=True)
    
    return jsonify({
        'error': True,
        'message': str(error),
        'status_code': status_code
    }), status_code


def log_error(error, user_id=None, additional_info=None):
    """Log an error with additional context."""
    logger.error(
        f"Error: {str(error)}",
        extra={
            'user_id': user_id,
            'additional_info': additional_info,
            'url': request.url,
            'method': request.method,
            'ip_address': request.remote_addr
        },
        exc_info=True
    )


def error_handler(f):
    """Decorator to handle errors in route functions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AuthenticationError as e:
            logger.warning(f"Authentication error: {str(e)}")
            return handle_error_response(str(e), 401)
        except AuthorizationError as e:
            logger.warning(f"Authorization error: {str(e)}")
            return handle_error_response(str(e), 403)
        except ValidationError as e:
            logger.info(f"Validation error: {str(e)}")
            return handle_error_response(str(e), 400)
        except DatabaseError as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            return handle_error_response("Database error occurred", 500)
        except SecurityError as e:
            logger.error(f"Security error: {str(e)}", exc_info=True)
            SecurityLog.log_event(
                event_type='SECURITY_ERROR',
                user_id=getattr(current_user, 'id', None),
                ip_address=request.remote_addr,
                details=str(e),
                severity='high'
            )
            return handle_error_response("Security error occurred", 403)
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}", exc_info=True)
            return handle_error_response("An unexpected error occurred", 500)
    return decorated_function