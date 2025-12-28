from app import db
from datetime import datetime
from sqlalchemy import and_

# Import scheduler only when needed to avoid circular imports
scheduler_instance = None

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    owner_name = db.Column(db.String(100), nullable=False)
    vehicle_type = db.Column(db.Enum('car', 'auto', 'bus', 'truck', 'bike', name='vehicle_types'), nullable=False)
    cng_test_date = db.Column(db.Date, nullable=True)
    cng_expiry_date = db.Column(db.Date, nullable=True)
    compliance_status = db.Column(db.Enum('valid', 'expiring_soon', 'expired', name='compliance_status'), 
                                  default='valid', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    compliance_records = db.relationship('ComplianceRecord', backref='vehicle', lazy=True)
    documents = db.relationship('Document', backref='vehicle', lazy=True, cascade='all, delete-orphan')
    qr_codes = db.relationship('QRCode', backref='vehicle', lazy=True, cascade='all, delete-orphan')
    
    def calculate_compliance_status(self):
        """Calculate compliance status based on expiry date"""
        if not self.cng_expiry_date:
            return 'valid'  # If no expiry date, consider valid
        
        today = datetime.utcnow().date()
        expiry_date = self.cng_expiry_date
        
        # Check if expired
        if today > expiry_date:
            return 'expired'
        
        # Check if expiring soon (within 30 days)
        days_to_expiry = (expiry_date - today).days
        if days_to_expiry <= 30:
            return 'expiring_soon'
        
        return 'valid'
    
    def days_to_expiry(self):
        """Calculate days remaining to expiry"""
        if not self.cng_expiry_date:
            return None
        
        today = datetime.utcnow().date()
        days = (self.cng_expiry_date - today).days
        return days if days > 0 else 0
    
    def update_compliance_status(self):
        """Update compliance status in the database"""
        self.compliance_status = self.calculate_compliance_status()
        db.session.commit()
        
        # Schedule reminders if scheduler is available
        global scheduler_instance
        if scheduler_instance:
            scheduler_instance.schedule_vehicle_expiry_reminders(self.id)
    
    def __repr__(self):
        return f'<Vehicle {self.vehicle_number}>'