from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models after db is defined
from .user import User
from .station import Station
from .vehicle import Vehicle
from .compliance import Compliance
from .document import Document
from .notification import Notification
from .qr_code import QRCode
from .rating import Rating
from .security_log import SecurityLog

# Export models
__all__ = ['db', 'User', 'Station', 'Vehicle', 'Compliance', 'Document', 'Notification', 'QRCode', 'Rating', 'SecurityLog']
