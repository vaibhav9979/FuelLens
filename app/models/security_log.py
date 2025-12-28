"""Security log model for tracking security events."""

from app import db
from datetime import datetime


class SecurityLog(db.Model):
    __tablename__ = 'security_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'LOGIN_ATTEMPT', 'FAILED_LOGIN', 'SUSPICIOUS_ACTIVITY'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=False)  # Supports both IPv4 and IPv6
    user_agent = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)  # Additional details about the event
    severity = db.Column(db.Enum('low', 'medium', 'high', 'critical', name='security_severity'), 
                        default='medium', nullable=False)
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='security_logs')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_security_logs')
    
    def __repr__(self):
        return f'<SecurityLog {self.event_type} at {self.timestamp}>'
    
    @classmethod
    def log_event(cls, event_type, user_id=None, ip_address=None, details=None, 
                  severity='medium', user_agent=None):
        """Create and save a security log entry."""
        from flask import request
        from app import db
        
        log_entry = cls(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address or request.remote_addr,
            user_agent=user_agent or request.headers.get('User-Agent'),
            details=details,
            severity=severity
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        return log_entry
    
    @classmethod
    def get_recent_events(cls, limit=50, severity=None, event_type=None):
        """Get recent security events."""
        query = cls.query.order_by(cls.timestamp.desc())
        
        if severity:
            query = query.filter_by(severity=severity)
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        return query.limit(limit).all()
    
    @classmethod
    def get_unresolved_events(cls, severity=None):
        """Get unresolved security events."""
        query = cls.query.filter_by(is_resolved=False).order_by(cls.timestamp.desc())
        
        if severity:
            query = query.filter_by(severity=severity)
        
        return query.all()
    
    def resolve(self, resolver_id=None):
        """Mark this security event as resolved."""
        self.is_resolved = True
        self.resolved_at = datetime.utcnow()
        self.resolved_by = resolver_id