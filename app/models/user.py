from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
from flask_login import UserMixin
from datetime import datetime, timedelta
import bcrypt
import jwt
from app import create_app
from app.utils.security import hash_password, verify_password

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # Increased length for bcrypt
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    role = db.Column(db.Enum('vehicle_owner', 'station_operator', 'admin', name='user_roles'), nullable=False, default='vehicle_owner')
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(255), nullable=True)
    password_reset_token = db.Column(db.String(255), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    password_reset_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owned_stations = db.relationship('FuelStation', back_populates='owner', lazy=True, overlaps='station')
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True, cascade='all, delete-orphan')
    compliance_records = db.relationship('ComplianceRecord', backref='checker', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    documents = db.relationship('Document', backref='owner', lazy=True, cascade='all, delete-orphan')
    station_ratings = db.relationship('StationRating', backref='rater', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password using security utility"""
        self.password_hash = hash_password(password)
    
    def check_password(self, password):
        """Check if provided password matches the hash using security utility"""
        return verify_password(password, self.password_hash)
    
    def get_reset_token(self, expires=500):
        """Generate a password reset token"""
        return jwt.encode(
            {'reset_password': self.id, 'exp': datetime.utcnow() + datetime.timedelta(seconds=expires)},
            create_app().config['SECRET_KEY'], algorithm='HS256'
        )
    
    @staticmethod
    def verify_reset_token(token):
        """Verify the password reset token"""
        try:
            id = jwt.decode(token, create_app().config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None
        return User.query.get(id)
    
    def get_full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def is_account_locked(self):
        """Check if the account is currently locked"""
        if self.account_locked_until and self.account_locked_until > datetime.utcnow():
            return True
        return False
    
    def lock_account(self, duration_minutes=30):
        """Lock the account for a specified duration"""
        self.account_locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.failed_login_attempts = 0  # Reset after locking
    
    def unlock_account(self):
        """Unlock the account"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
    
    def increment_failed_login(self):
        """Increment the failed login attempts counter"""
        self.failed_login_attempts += 1
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account()
    
    def reset_failed_login_attempts(self):
        """Reset the failed login attempts counter"""
        self.failed_login_attempts = 0
    
    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()
        self.reset_failed_login_attempts()  # Reset on successful login
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def get_assigned_station(self):
        """Get the assigned station for this user if they are a station operator"""
        # Late import to avoid circular import
        from app.models.station import StationEmployee
        
        assignment = StationEmployee.query.filter_by(employee_id=self.id, is_active=True).first()
        if assignment:
            return assignment.station

        return None
