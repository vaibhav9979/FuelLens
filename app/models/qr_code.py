from app import db
from datetime import datetime

class QRCode(db.Model):
    __tablename__ = 'qr_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    qr_code_path = db.Column(db.String(255), nullable=False)  # Path to QR code image file
    qr_content = db.Column(db.Text, nullable=False)  # Encoded content
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<QRCode for Vehicle {self.vehicle_id}>'