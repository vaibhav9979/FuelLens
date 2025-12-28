"""Notifications service for FuelLens application."""

from datetime import datetime
from app.models import Notification, User
from app import db
from app.utils.helpers import sanitize_input


class NotificationService:
    """Service for handling notifications."""
    
    @staticmethod
    def create_notification(user_id, title, message, notification_type='system', priority='normal'):
        """Create a new notification."""
        # Sanitize inputs
        title = sanitize_input(title) if title else title
        message = sanitize_input(message) if message else message
        
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority
        )
        
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def get_user_notifications(user_id, limit=10, offset=0, unread_only=False):
        """Get notifications for a user."""
        query = Notification.query.filter_by(user_id=user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def mark_notification_as_read(notification_id):
        """Mark a notification as read."""
        notification = Notification.query.get(notification_id)
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications for a user as read."""
        notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        db.session.commit()
        return len(notifications)
    
    @staticmethod
    def delete_notification(notification_id, user_id):
        """Delete a notification."""
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notification:
            db.session.delete(notification)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_unread_count(user_id):
        """Get count of unread notifications for a user."""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    @staticmethod
    def send_system_notification(user_id, title, message):
        """Send a system notification."""
        return NotificationService.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type='system'
        )
    
    @staticmethod
    def send_compliance_notification(user_id, title, message):
        """Send a compliance-related notification."""
        return NotificationService.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type='compliance',
            priority='high'
        )
    
    @staticmethod
    def send_alert_notification(user_id, title, message):
        """Send an alert notification."""
        return NotificationService.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type='alert',
            priority='high'
        )
    
    @staticmethod
    def bulk_create_notifications(user_ids, title, message, notification_type='system'):
        """Create notifications for multiple users."""
        notifications = []
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                title=sanitize_input(title),
                message=sanitize_input(message),
                notification_type=notification_type
            )
            notifications.append(notification)
            db.session.add(notification)
        
        db.session.commit()
        return notifications