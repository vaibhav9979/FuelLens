from app.models import User, Vehicle, ComplianceRecord, FuelStation, Document, StationRating
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
import json

class ReportingService:
    def __init__(self):
        pass
    
    def get_user_statistics(self):
        """Get user-related statistics"""
        stats = {}
        
        # Total users
        stats['total_users'] = User.query.count()
        
        # Users by role
        stats['vehicle_owners'] = User.query.filter_by(role='vehicle_owner').count()
        stats['station_operators'] = User.query.filter_by(role='station_operator').count()
        stats['admins'] = User.query.filter_by(role='admin').count()
        
        # Active vs inactive users
        stats['active_users'] = User.query.filter_by(is_active=True).count()
        stats['inactive_users'] = User.query.filter_by(is_active=False).count()
        
        return stats
    
    def get_vehicle_statistics(self):
        """Get vehicle-related statistics"""
        stats = {}
        
        # Total vehicles
        stats['total_vehicles'] = Vehicle.query.count()
        
        # Vehicles by compliance status
        stats['valid_vehicles'] = Vehicle.query.filter_by(compliance_status='valid').count()
        stats['expiring_vehicles'] = Vehicle.query.filter_by(compliance_status='expiring_soon').count()
        stats['expired_vehicles'] = Vehicle.query.filter_by(compliance_status='expired').count()
        
        # Vehicles by type
        vehicle_types = db.session.query(
            Vehicle.vehicle_type, 
            func.count(Vehicle.id)
        ).group_by(Vehicle.vehicle_type).all()
        
        stats['vehicles_by_type'] = {vtype: count for vtype, count in vehicle_types}
        
        return stats
    
    def get_compliance_statistics(self):
        """Get compliance-related statistics"""
        stats = {}
        
        # Total compliance checks
        stats['total_checks'] = ComplianceRecord.query.count()
        
        # Checks by status
        stats['valid_checks'] = ComplianceRecord.query.filter_by(compliance_status='valid').count()
        stats['expiring_checks'] = ComplianceRecord.query.filter_by(compliance_status='expiring_soon').count()
        stats['expired_checks'] = ComplianceRecord.query.filter_by(compliance_status='expired').count()
        
        # Checks by type
        stats['camera_checks'] = ComplianceRecord.query.filter_by(check_type='camera').count()
        stats['qr_checks'] = ComplianceRecord.query.filter_by(check_type='qr').count()
        stats['manual_checks'] = ComplianceRecord.query.filter_by(check_type='manual').count()
        
        return stats
    
    def get_station_statistics(self):
        """Get station-related statistics"""
        stats = {}
        
        # Total stations
        stats['total_stations'] = FuelStation.query.count()
        
        # Active vs inactive stations
        stats['active_stations'] = FuelStation.query.filter_by(is_active=True).count()
        stats['inactive_stations'] = FuelStation.query.filter_by(is_active=False).count()
        
        # Open vs closed stations
        stats['open_stations'] = FuelStation.query.filter_by(is_open=True).count()
        stats['closed_stations'] = FuelStation.query.filter_by(is_open=False).count()
        
        # Stations by load
        free_stations = FuelStation.query.filter_by(live_load='free').count()
        normal_stations = FuelStation.query.filter_by(live_load='normal').count()
        busy_stations = FuelStation.query.filter_by(live_load='busy').count()
        
        stats['load_distribution'] = {
            'free': free_stations,
            'normal': normal_stations,
            'busy': busy_stations
        }
        
        return stats
    
    def get_daily_compliance_trends(self, days=7):
        """Get daily compliance check trends"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Get daily counts
        daily_counts = db.session.query(
            func.date(ComplianceRecord.created_at).label('date'),
            func.count(ComplianceRecord.id).label('count'),
            func.sum(func.case((ComplianceRecord.compliance_status == 'valid', 1), else_=0)).label('valid'),
            func.sum(func.case((ComplianceRecord.compliance_status == 'expiring_soon', 1), else_=0)).label('expiring'),
            func.sum(func.case((ComplianceRecord.compliance_status == 'expired', 1), else_=0)).label('expired')
        ).filter(
            func.date(ComplianceRecord.created_at) >= start_date,
            func.date(ComplianceRecord.created_at) <= end_date
        ).group_by(func.date(ComplianceRecord.created_at)).order_by(func.date(ComplianceRecord.created_at)).all()
        
        # Create complete date range
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        # Format data for chart
        chart_data = {
            'dates': date_range,
            'total': [],
            'valid': [],
            'expiring': [],
            'expired': []
        }
        
        # Create a map of existing data
        date_map = {str(row.date): {
            'total': row.count,
            'valid': row.valid or 0,
            'expiring': row.expiring or 0,
            'expired': row.expired or 0
        } for row in daily_counts}
        
        # Fill in the chart data
        for date in date_range:
            if date in date_map:
                chart_data['total'].append(date_map[date]['total'])
                chart_data['valid'].append(date_map[date]['valid'])
                chart_data['expiring'].append(date_map[date]['expiring'])
                chart_data['expired'].append(date_map[date]['expired'])
            else:
                chart_data['total'].append(0)
                chart_data['valid'].append(0)
                chart_data['expiring'].append(0)
                chart_data['expired'].append(0)
        
        return chart_data
    
    def get_top_stations_by_compliance(self, limit=10):
        """Get top stations by compliance activity"""
        top_stations = db.session.query(
            FuelStation.name,
            func.count(ComplianceRecord.id).label('checks'),
            func.avg(
                func.case(
                    (ComplianceRecord.compliance_status == 'valid', 100),
                    (ComplianceRecord.compliance_status == 'expiring_soon', 50),
                    (ComplianceRecord.compliance_status == 'expired', 0),
                    else_=0
                )
            ).label('avg_compliance_score')
        ).join(ComplianceRecord, FuelStation.id == ComplianceRecord.station_id)\
         .group_by(FuelStation.id, FuelStation.name)\
         .order_by(func.count(ComplianceRecord.id).desc())\
         .limit(limit).all()
        
        return [{'name': station[0], 'checks': station[1], 'score': float(station[2] or 0)} for station in top_stations]
    
    def get_compliance_by_vehicle_type(self):
        """Get compliance statistics by vehicle type"""
        result = db.session.query(
            Vehicle.vehicle_type,
            func.count(Vehicle.id).label('total'),
            func.sum(func.case((Vehicle.compliance_status == 'valid', 1), else_=0)).label('valid'),
            func.sum(func.case((Vehicle.compliance_status == 'expiring_soon', 1), else_=0)).label('expiring'),
            func.sum(func.case((Vehicle.compliance_status == 'expired', 1), else_=0)).label('expired')
        ).group_by(Vehicle.vehicle_type).all()
        
        return [{
            'type': row[0],
            'total': row[1],
            'valid': row[2] or 0,
            'expiring': row[3] or 0,
            'expired': row[4] or 0
        } for row in result]
    
    def get_monthly_report(self, year=None, month=None):
        """Get comprehensive monthly report"""
        if year is None:
            year = datetime.utcnow().year
        if month is None:
            month = datetime.utcnow().month
        
        # Get start and end dates for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # Get data for the month
        users_joined = User.query.filter(
            User.created_at >= start_date,
            User.created_at < end_date
        ).count()
        
        vehicles_added = Vehicle.query.filter(
            Vehicle.created_at >= start_date,
            Vehicle.created_at < end_date
        ).count()
        
        compliance_checks = ComplianceRecord.query.filter(
            ComplianceRecord.created_at >= start_date,
            ComplianceRecord.created_at < end_date
        ).count()
        
        report = {
            'period': f"{start_date.strftime('%B')} {year}",
            'users_joined': users_joined,
            'vehicles_added': vehicles_added,
            'compliance_checks': compliance_checks,
            'user_stats': self.get_user_statistics(),
            'vehicle_stats': self.get_vehicle_statistics(),
            'compliance_stats': self.get_compliance_statistics(),
            'station_stats': self.get_station_statistics()
        }
        
        return report
    
    def generate_pdf_report(self, report_data):
        """Generate a PDF report (placeholder - would use a PDF library in real implementation)"""
        # This is a placeholder implementation
        # In a real application, you would use a library like reportlab or weasyprint
        import io
        pdf_content = f"""
        FUELLENS COMPLIANCE REPORT
        ==========================
        
        Period: {report_data.get('period', 'N/A')}
        
        USERS:
        - Total Users: {report_data['user_stats']['total_users']}
        - Vehicle Owners: {report_data['user_stats']['vehicle_owners']}
        - Station Operators: {report_data['user_stats']['station_operators']}
        - Admins: {report_data['user_stats']['admins']}
        
        VEHICLES:
        - Total Vehicles: {report_data['vehicle_stats']['total_vehicles']}
        - Valid Compliance: {report_data['vehicle_stats']['valid_vehicles']}
        - Expiring Soon: {report_data['vehicle_stats']['expiring_vehicles']}
        - Expired: {report_data['vehicle_stats']['expired_vehicles']}
        
        COMPLIANCE:
        - Total Checks: {report_data['compliance_stats']['total_checks']}
        - Valid Checks: {report_data['compliance_stats']['valid_checks']}
        - Expiring Checks: {report_data['compliance_stats']['expiring_checks']}
        - Expired Checks: {report_data['compliance_stats']['expired_checks']}
        
        Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return pdf_content.encode('utf-8')