from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_session import Session
from dotenv import load_dotenv
import os

# Setup logging first
from app.utils.logging_config import setup_logging
from app.utils.error_handler import init_error_handlers

load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
cache = Cache()
session = Session()

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Setup logging based on config
    log_level = 'DEBUG' if config_name == 'development' else 'INFO'
    setup_logging(log_level)
    
    # Load configuration
    if config_name == 'development':
        from config.development import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    elif config_name == 'production':
        from config.production import ProductionConfig
        app.config.from_object(ProductionConfig)
    elif config_name == 'testing':
        from config.testing import TestingConfig
        app.config.from_object(TestingConfig)
    else:
        from config.base import Config
        app.config.from_object(Config)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    session.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Initialize error handlers
    init_error_handlers(app)
    
    # Register blueprints
    from app.controllers.auth import auth_bp
    from app.controllers.user import user_bp
    from app.controllers.operator import operator_bp
    from app.controllers.admin import admin_bp
    from app.controllers.main import main_bp
    from app.controllers.stations import stations_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(operator_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(stations_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app