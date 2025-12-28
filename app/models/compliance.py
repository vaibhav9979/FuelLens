from app import db
from datetime import datetime

class ComplianceRecord(db.Model):
    __tablename__ = 'compliance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('fuel_stations.id'), nullable=False)
    checker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    check_type = db.Column(db.Enum('camera', 'qr', 'manual', name='check_types'), nullable=False)
    compliance_status = db.Column(db.String(20), nullable=False)  # valid, expired, expiring_soon
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    

    
    def __repr__(self):
        return f'<ComplianceRecord {self.vehicle_id} at {self.station_id}>'