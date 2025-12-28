from flask_mail import Message
from app import mail, db
from datetime import datetime, timedelta
from app.models import Notification
from .security import validate_vehicle_number, sanitize_input
import re

def send_email(subject, recipients, body):
    """Send email using Flask-Mail"""
    msg = Message(subject, recipients=recipients)
    msg.body = body
    mail.send(msg)

def calculate_compliance_status(expiry_date):
    """Calculate compliance status based on expiry date"""
    if not expiry_date:
        return 'valid'  # If no expiry date, consider valid
    
    today = datetime.utcnow().date()
    
    # Check if expired
    if today > expiry_date:
        return 'expired'
    
    # Check if expiring soon (within 30 days)
    days_to_expiry = (expiry_date - today).days
    if days_to_expiry <= 30:
        return 'expiring_soon'
    
    return 'valid'

def send_notification(user_id, title, message, notification_type='system'):
    """Create and save notification for a user"""
    from app.models import User
    
    # Sanitize inputs to prevent XSS
    title = sanitize_input(title) if title else title
    message = sanitize_input(message) if message else message
    
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type
    )
    
    db.session.add(notification)
    db.session.commit()

def send_compliance_reminder(vehicle):
    """Send compliance expiry reminder based on days to expiry"""
    days_to_expiry = vehicle.days_to_expiry()
    
    if days_to_expiry is None:
        return
    
    message = ""
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
        return  # No need to send reminder
    
    send_notification(
        user_id=vehicle.user_id,
        title=title,
        message=message,
        notification_type='compliance_expiry'
    )

def generate_qr_content(vehicle_id, vehicle_number, expiry_date):
    """Generate QR code content with vehicle info"""
    import json
    from datetime import datetime
    
    # Sanitize vehicle number
    vehicle_number = sanitize_input(vehicle_number) if vehicle_number else vehicle_number
    
    qr_data = {
        'vehicle_id': vehicle_id,
        'vehicle_number': vehicle_number,
        'expiry_date': expiry_date.isoformat() if expiry_date else None,
        'generated_at': datetime.utcnow().isoformat(),
        'status': 'valid'  # This will be checked against database when scanned
    }
    
    return json.dumps(qr_data)

def validate_and_sanitize_input(input_string):
    """Validate and sanitize user input"""
    if not input_string:
        return input_string
    
    # Sanitize the input
    sanitized = sanitize_input(input_string)
    
    # Additional validation could be added here
    return sanitized