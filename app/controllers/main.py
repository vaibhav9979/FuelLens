from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, Vehicle, FuelStation
from app import db
import os
from flask import send_file


main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Get some statistics for the homepage
    total_stations = FuelStation.query.count()
    total_vehicles = Vehicle.query.count()
    total_users = User.query.count()
    
    return render_template('index.html', 
                          total_stations=total_stations,
                          total_vehicles=total_vehicles,
                          total_users=total_users)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Redirect to appropriate dashboard based on user role
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'station_operator':
        return redirect(url_for('operator.dashboard'))
    else:  # vehicle_owner
        return redirect(url_for('user.dashboard'))

@main_bp.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    # Security: Prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        from flask import abort
        return abort(404)
    
    # Construct the full path to the uploaded file
    upload_path = os.path.join('app', 'uploads', filename)
    
    # Check if file exists and user has permission to access it
    if os.path.exists(upload_path):
        return send_file(upload_path)
    else:
        from flask import abort
        return abort(404)

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        # In a real implementation, you would send an email or save the message
        # For now, just show a success message
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    
    return render_template('contact.html')