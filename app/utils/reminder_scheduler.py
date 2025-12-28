from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app import create_app, db
from app.models import Vehicle, Notification, User
from app.utils.helpers import send_compliance_reminder, send_email
from datetime import datetime, timedelta

class ReminderScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.app = create_app()
        
    def start(self):
        """Start the reminder scheduler"""
        # Schedule daily compliance check at 9 AM
        self.scheduler.add_job(
            func=self.daily_compliance_check,
            trigger=CronTrigger(hour=9, minute=0),  # Every day at 9 AM
            id='daily_compliance_check',
            name='Daily compliance status check',
            replace_existing=True
        )
        
        # Schedule weekly report at Sunday 10 AM
        self.scheduler.add_job(
            func=self.weekly_report,
            trigger=CronTrigger(day_of_week=6, hour=10, minute=0),  # Every Sunday at 10 AM
            id='weekly_report',
            name='Weekly compliance report',
            replace_existing=True
        )
        
        self.scheduler.start()
        print("Reminder scheduler started...")
        
    def stop(self):
        """Stop the reminder scheduler"""
        self.scheduler.shutdown()
        print("Reminder scheduler stopped...")
        
    def daily_compliance_check(self):
        """Check compliance status for all vehicles and send reminders if needed"""
        print(f"Running daily compliance check at {datetime.utcnow()}")
        
        with self.app.app_context():
            # Get all vehicles that are expiring soon or expired
            vehicles = Vehicle.query.all()
            
            for vehicle in vehicles:
                # Update compliance status
                vehicle.update_compliance_status()
                
                # Send reminder if needed
                send_compliance_reminder(vehicle)
    
    def weekly_report(self):
        """Generate and send weekly compliance report"""
        print(f"Generating weekly report at {datetime.utcnow()}")
        
        with self.app.app_context():
            # Calculate some basic stats
            total_vehicles = Vehicle.query.count()
            valid_vehicles = Vehicle.query.filter_by(compliance_status='valid').count()
            expiring_vehicles = Vehicle.query.filter_by(compliance_status='expiring_soon').count()
            expired_vehicles = Vehicle.query.filter_by(compliance_status='expired').count()
            
            # Get admin users to send the report to
            admin_users = User.query.filter_by(role='admin').all()
            
            report_message = f"""
Weekly Compliance Report - {datetime.utcnow().strftime('%Y-%m-%d')}

Total Vehicles: {total_vehicles}
Valid Compliance: {valid_vehicles}
Expiring Soon: {expiring_vehicles}
Expired: {expired_vehicles}

Compliance Rate: {valid_vehicles/total_vehicles*100:.2f if total_vehicles > 0 else 0.0}%

Please log in to the admin panel for detailed reports and analytics.
            """
            
            for admin in admin_users:
                # Send notification
                notification = Notification(
                    user_id=admin.id,
                    title="Weekly Compliance Report",
                    message=report_message.strip(),
                    notification_type="system"
                )
                db.session.add(notification)
                
                # Optionally send email (if email is configured)
                if admin.email:
                    try:
                        send_email(
                            subject="Weekly Compliance Report",
                            recipients=[admin.email],
                            body=report_message.strip()
                        )
                    except Exception as e:
                        print(f"Error sending email to {admin.email}: {e}")
            
            db.session.commit()
    
    def send_expiry_reminder(self, vehicle_id, days_before_expiry):
        """Send a specific reminder for a vehicle expiring in N days"""
        with self.app.app_context():
            vehicle = Vehicle.query.get(vehicle_id)
            if vehicle:
                # Calculate days to expiry
                days_to_expiry = vehicle.days_to_expiry()
                
                if days_to_expiry == days_before_expiry:
                    # Send reminder
                    message = f"Your CNG compliance for vehicle {vehicle.vehicle_number} expires in {days_before_expiry} day(s). Please renew soon."
                    title = f"CNG Compliance Reminder ({days_before_expiry} days)"
                    
                    from app.utils.helpers import send_notification
                    send_notification(
                        user_id=vehicle.user_id,
                        title=title,
                        message=message,
                        notification_type='compliance_expiry'
                    )
    
    def schedule_vehicle_expiry_reminders(self, vehicle_id):
        """Schedule reminders for a specific vehicle at 30, 15, 7, and 1 day(s) before expiry"""
        from apscheduler.triggers.date import DateTrigger
        
        with self.app.app_context():
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle or not vehicle.cng_expiry_date:
                return
            
            # Schedule reminders at specific intervals before expiry
            days_before = [30, 15, 7, 1]  # Days before expiry to send reminders
            
            for days in days_before:
                # Calculate the date when the reminder should be sent
                reminder_date = vehicle.cng_expiry_date - timedelta(days=days)
                
                # Only schedule if the reminder date is in the future
                if reminder_date > datetime.utcnow().date():
                    # Schedule the reminder
                    run_date = datetime.combine(reminder_date, datetime.min.time().replace(hour=9))  # At 9 AM
                    self.scheduler.add_job(
                        func=self.send_expiry_reminder,
                        trigger=DateTrigger(run_date=run_date),
                        id=f'reminder_{vehicle_id}_{days}',
                        args=[vehicle_id, days],
                        replace_existing=True
                    )