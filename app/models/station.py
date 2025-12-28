from app import db
from datetime import datetime

class FuelStation(db.Model):
    __tablename__ = 'fuel_stations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_open = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # New field for approval status
    approval_date = db.Column(db.DateTime, nullable=True)  # When the station was approved
    approval_notes = db.Column(db.Text, nullable=True)  # Notes from admin during approval
    live_load = db.Column(db.Enum('free', 'normal', 'busy', name='station_load_status'), default='normal')
    fuel_availability = db.Column(db.Enum('available', 'limited', 'unavailable', name='fuel_availability_status'), default='available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = db.relationship('User', foreign_keys=[owner_id], back_populates='owned_stations', overlaps='owned_stations')
    employees = db.relationship('User', backref='station', lazy=True, overlaps='station')
    compliance_records = db.relationship('ComplianceRecord', backref='station', lazy=True)
    ratings = db.relationship('StationRating', backref='station', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FuelStation {self.name}>'
    
    def get_full_address(self):
        """Get the full address of the station"""
        return f"{self.address}, {self.city}, {self.state} - {self.pincode}"

    def approve_station(self, admin_user_id=None, notes=None):
        """Approve the station"""
        self.is_approved = True
        self.approval_date = datetime.utcnow()
        self.approval_notes = notes
        if admin_user_id:
            # In a real app, you might want to track who approved the station
            pass


class StationEmployee(db.Model):
    __tablename__ = 'station_employees'
    
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('fuel_stations.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='operator')
    is_active = db.Column(db.Boolean, default=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    station = db.relationship('FuelStation', backref='station_employees')
    employee = db.relationship('User', backref='assigned_stations')
    
    def __repr__(self):
        return f'<StationEmployee {self.employee_id} at {self.station_id}>'