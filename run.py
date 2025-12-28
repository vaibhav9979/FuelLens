import os
from app import create_app
from app.models import User, Vehicle, FuelStation
from app.utils.reminder_scheduler import ReminderScheduler
from app import db


def create_initial_data():
    """Create initial data for the application"""
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        # Check if admin user already exists
        admin = User.query.filter_by(email='admin@fuellens.com').first()
        if not admin:
            admin = User(
                email='admin@fuellens.com',
                first_name='Admin',
                last_name='User',
                role='admin'
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            db.session.commit()
            print("Created admin user: admin@fuellens.com / admin123")
        
        # Check if sample station exists
        station = FuelStation.query.filter_by(name='Sample Fuel Station').first()
        if not station:
            station = FuelStation(
                name='Sample Fuel Station',
                owner_id=admin.id,
                address='123 Main Street',
                city='Mumbai',
                state='Maharashtra',
                pincode='400001',
                phone='+91-9876543210',
                email='station@example.com',
                is_active=True,
                is_open=True
            )
            db.session.add(station)
            db.session.commit()
            print("Created sample fuel station")

if __name__ == '__main__':
    # Determine the environment
    env = os.getenv('FLASK_ENV', 'development')
    
    # Create initial data if tables are empty
    create_initial_data()
    
    # Create the Flask app with appropriate configuration
    app = create_app(env)
    
    # Initialize and start the reminder scheduler
    scheduler = ReminderScheduler()
    scheduler.start()
    
    # Print startup information
    print(f"Starting FuelLens application in {env} mode...")
    print("Admin user: admin@fuellens.com / admin123")
    print("Visit http://localhost:5000 to access the application")
    
    # Run the app
    if env == 'development':
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # In production, don't use Flask's development server
        print("Production mode - use a production WSGI server like Gunicorn")
        # For local testing of production config only:
        app.run(debug=False, host='0.0.0.0', port=5000)
    
    # Clean up scheduler on exit
    try:
        scheduler.stop()
    except Exception as e:
        print(f'Error stopping scheduler: {e}')