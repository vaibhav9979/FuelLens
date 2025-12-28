"""Compliance service for FuelLens application."""

from datetime import datetime, timedelta
from app.models import Vehicle, ComplianceRecord, Notification, FuelStation
from app import db
from app.utils.helpers import calculate_compliance_status, send_notification


class ComplianceService:
    """Service for handling compliance-related operations."""
    
    @staticmethod
    def check_vehicle_compliance(vehicle_id):
        """Check compliance status for a vehicle."""
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        return calculate_compliance_status(vehicle.cng_expiry_date)
    
    @staticmethod
    def record_compliance_check(vehicle_id, station_id, checker_id, check_type='manual', notes=''):
        """Record a compliance check."""
        from app.models import User  # Import here to avoid circular import
        
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        station = FuelStation.query.get_or_404(station_id)
        checker = User.query.get_or_404(checker_id)
        
        compliance_status = calculate_compliance_status(vehicle.cng_expiry_date)
        
        compliance_record = ComplianceRecord(
            vehicle_id=vehicle.id,
            station_id=station.id,
            checker_id=checker.id,
            check_type=check_type,
            compliance_status=compliance_status,
            notes=notes
        )
        
        db.session.add(compliance_record)
        db.session.commit()
        
        # Update vehicle's compliance status
        vehicle.update_compliance_status()
        
        return compliance_record
    
    @staticmethod
    def get_compliance_history(vehicle_id, limit=10):
        """Get compliance history for a vehicle."""
        return ComplianceRecord.query.filter_by(vehicle_id=vehicle_id).order_by(
            ComplianceRecord.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_station_compliance_stats(station_id):
        """Get compliance statistics for a station."""
        from sqlalchemy import func
        
        stats = db.session.query(
            ComplianceRecord.compliance_status,
            func.count(ComplianceRecord.id).label('count')
        ).filter_by(station_id=station_id).group_by(ComplianceRecord.compliance_status).all()
        
        return {status: count for status, count in stats}
    
    @staticmethod
    def send_compliance_reminders():
        """Send compliance expiry reminders for all vehicles."""
        vehicles = Vehicle.query.all()
        sent_count = 0
        
        for vehicle in vehicles:
            days_to_expiry = vehicle.days_to_expiry()
            
            if days_to_expiry is None:
                continue
            
            message = ""
            title = ""
            
            if days_to_expiry == 0:
                message = f"Your CNG compliance for vehicle {vehicle.vehicle_number} has expired today!"
                title = "CNG Compliance Expired"
            elif days_to_expiry <= 7:
                message = f"Your CNG compliance for vehicle {vehicle.vehicle_number} expires in {days_to_expiry} day(s). Please renew soon."
                title = f"CNG Compliance Expiring Soon ({days_to_expiry} days)"
            elif days_to_expiry <= 30:
                message = f"Your CNG compliance for vehicle {vehicle.vehicle_number} expires in {days_to_expiry} day(s). Plan for renewal."
                title = f"CNG Compliance Reminder ({days_to_expiry} days)"
            else:
                continue  # No need to send reminder
            
            send_notification(
                user_id=vehicle.user_id,
                title=title,
                message=message,
                notification_type='compliance_expiry'
            )
            sent_count += 1
        
        return sent_count
    
    @staticmethod
    def get_compliance_trends(days=30):
        """Get compliance trends for the last N days."""
        from sqlalchemy import func, case
        from datetime import date
        
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        trends = db.session.query(
            func.date(ComplianceRecord.created_at).label('date'),
            func.count(ComplianceRecord.id).label('checks'),
            func.sum(case([(ComplianceRecord.compliance_status == 'valid', 1)], else_=0)).label('valid'),
            func.sum(case([(ComplianceRecord.compliance_status == 'expiring_soon', 1)], else_=0)).label('expiring_soon'),
            func.sum(case([(ComplianceRecord.compliance_status == 'expired', 1)], else_=0)).label('expired')
        ).filter(
            ComplianceRecord.created_at >= start_date
        ).group_by(func.date(ComplianceRecord.created_at)).order_by('date').all()
        
        return trends