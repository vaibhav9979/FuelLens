from app import db
from datetime import datetime

class StationRating(db.Model):
    __tablename__ = 'station_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('fuel_stations.id'), nullable=False)
    rater_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    compliance_strictness = db.Column(db.Integer, nullable=False)  # 1-5 rating
    waiting_time = db.Column(db.Integer, nullable=False)  # 1-5 rating
    service_quality = db.Column(db.Integer, nullable=False)  # 1-5 rating
    overall_rating = db.Column(db.Float, nullable=False)  # Average of all ratings
    review = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Rating for Station {self.station_id} by User {self.rater_id}>'