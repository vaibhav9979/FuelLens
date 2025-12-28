from app import db
from datetime import datetime

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    document_type = db.Column(db.Enum('rc', 'insurance', 'puc', 'cng_certificate', 'other', name='document_types'), nullable=False)
    document_name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # in bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.Date, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Document {self.document_type} for {self.user_id}>'