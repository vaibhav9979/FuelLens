from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Vehicle, ComplianceRecord, Document, QRCode, Notification, FuelStation
from app.utils.helpers import send_compliance_reminder, generate_qr_content
import qrcode
import os
from datetime import datetime
import json


user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'vehicle_owner':
        # Get user's vehicles
        vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
        
        # Get recent compliance records for user's vehicles
        recent_compliance = []
        for vehicle in vehicles:
            records = ComplianceRecord.query.filter_by(vehicle_id=vehicle.id).order_by(ComplianceRecord.created_at.desc()).limit(5).all()
            recent_compliance.extend(records)
        
        # Sort by date and get top 5
        recent_compliance = sorted(recent_compliance, key=lambda x: x.created_at, reverse=True)[:5]
        
        # Get unread notifications
        notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
        
        return render_template('user/dashboard.html', 
                              vehicles=vehicles, 
                              recent_compliance=recent_compliance,
                              notifications=notifications)
    elif current_user.role == 'station_operator':
        # For station operators, redirect to operator dashboard
        return redirect(url_for('operator.dashboard'))
    else:
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))

@user_bp.route('/register-station', methods=['GET', 'POST'])
@login_required
def register_station():
    # Only allow station operators to register stations
    if current_user.role != 'station_operator':
        flash('Access denied. Only station operators can register stations.', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        pincode = request.form.get('pincode', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        
        # Validation
        if not all([name, address, city, state, pincode]):
            flash('All required fields must be filled!', 'error')
            return render_template('user/register_station.html')
        
        # Validate pincode format
        if len(pincode) != 6 or not pincode.isdigit():
            flash('Invalid pincode format. Pincode must be 6 digits.', 'error')
            return render_template('user/register_station.html')
        
        # Create new fuel station with is_approved=False (needs admin approval)
        station = FuelStation(
            name=name,
            owner_id=current_user.id,  # Station operator is the owner of the station
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            phone=phone,
            email=email,
            latitude=latitude,
            longitude=longitude,
            is_approved=False,  # Requires admin approval
            is_active=True  # Active but not approved yet
        )
        
        try:
            db.session.add(station)
            db.session.commit()
            
            flash('Fuel station registered successfully! It will be activated after admin approval.', 'success')
            return redirect(url_for('user.my_stations'))
        except Exception as e:
            db.session.rollback()
            flash('Error registering fuel station. Please try again.', 'error')
    
    return render_template('user/register_station.html')

@user_bp.route('/my-stations')
@login_required
def my_stations():
    # Only allow station operators to view their stations
    if current_user.role != 'station_operator':
        flash('Access denied. Only station operators can view stations.', 'error')
        return redirect(url_for('main.index'))
    
    # Get stations owned by this user
    stations = FuelStation.query.filter_by(owner_id=current_user.id).all()
    
    return render_template('user/my_stations.html', stations=stations)

@user_bp.route('/vehicles')
@login_required
def vehicles():
    if current_user.role != 'vehicle_owner':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    user_vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template('user/vehicles.html', vehicles=user_vehicles)

@user_bp.route('/vehicle/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if current_user.role != 'vehicle_owner':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get vehicle number from query parameter if available
    vehicle_number = request.args.get('vehicle_number', '').strip().upper()
    
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number', '').strip().upper()
        owner_name = request.form.get('owner_name', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'car')
        cng_test_date = request.form.get('cng_test_date')
        cng_expiry_date = request.form.get('cng_expiry_date')
        
        # Validation
        if not all([vehicle_number, owner_name, vehicle_type]):
            flash('Vehicle number, owner name, and vehicle type are required!', 'error')
            return render_template('user/add_vehicle.html', prefill_vehicle_number=vehicle_number)
        
        # Check if vehicle number already exists
        existing_vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number).first()
        if existing_vehicle:
            flash('Vehicle number already exists in the system!', 'error')
            return render_template('user/add_vehicle.html', prefill_vehicle_number=vehicle_number)
        
        # Convert dates if provided
        from datetime import datetime
        test_date = datetime.strptime(cng_test_date, '%Y-%m-%d').date() if cng_test_date else None
        expiry_date = datetime.strptime(cng_expiry_date, '%Y-%m-%d').date() if cng_expiry_date else None
        
        try:
            # Create new vehicle
            vehicle = Vehicle(
                user_id=current_user.id,
                vehicle_number=vehicle_number,
                owner_name=owner_name,
                vehicle_type=vehicle_type,
                cng_test_date=test_date,
                cng_expiry_date=expiry_date
            )
            
            # Calculate compliance status
            vehicle.update_compliance_status()
            
            db.session.add(vehicle)
            db.session.commit()
            
            # Generate QR code for the vehicle
            qr_content = generate_qr_content(vehicle.id, vehicle.vehicle_number, vehicle.cng_expiry_date)
            
            # Create QR code image
            qr_img = qrcode.make(qr_content)
            qr_filename = f"qr_{vehicle.id}_{vehicle.vehicle_number.replace(' ', '_')}.png"
            qr_path = os.path.join('app', 'static', 'qr_codes', qr_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(qr_path), exist_ok=True)
            
            qr_img.save(qr_path)
            
            # Save QR code record to database
            qr_code = QRCode(
                vehicle_id=vehicle.id,
                qr_code_path=qr_path,
                qr_content=qr_content
            )
            db.session.add(qr_code)
            db.session.commit()
            
            flash('Vehicle added successfully!', 'success')
            return redirect(url_for('user.vehicles'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding vehicle. Please try again.', 'error')
    
    return render_template('user/add_vehicle.html', prefill_vehicle_number=vehicle_number)

@user_bp.route('/vehicle/<int:vehicle_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vehicle_id):
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        owner_name = request.form.get('owner_name', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'car')
        cng_test_date = request.form.get('cng_test_date')
        cng_expiry_date = request.form.get('cng_expiry_date')
        
        # Validation
        if not all([owner_name, vehicle_type]):
            flash('Owner name and vehicle type are required!', 'error')
            return render_template('user/edit_vehicle.html', vehicle=vehicle)
        
        # Convert dates if provided
        from datetime import datetime
        test_date = datetime.strptime(cng_test_date, '%Y-%m-%d').date() if cng_test_date else None
        expiry_date = datetime.strptime(cng_expiry_date, '%Y-%m-%d').date() if cng_expiry_date else None
        
        try:
            # Update vehicle
            vehicle.owner_name = owner_name
            vehicle.vehicle_type = vehicle_type
            vehicle.cng_test_date = test_date
            vehicle.cng_expiry_date = expiry_date
            
            # Update compliance status
            vehicle.update_compliance_status()
            
            db.session.commit()
            flash('Vehicle updated successfully!', 'success')
            return redirect(url_for('user.vehicles'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating vehicle. Please try again.', 'error')
    
    return render_template('user/edit_vehicle.html', vehicle=vehicle)

@user_bp.route('/vehicle/<int:vehicle_id>/delete', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first_or_404()
    
    try:
        # Delete related records first
        # Delete QR codes
        qr_codes = QRCode.query.filter_by(vehicle_id=vehicle.id).all()
        for qr in qr_codes:
            if os.path.exists(qr.qr_code_path):
                os.remove(qr.qr_code_path)
            db.session.delete(qr)
        
        # Delete documents
        documents = Document.query.filter_by(vehicle_id=vehicle.id).all()
        for doc in documents:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
            db.session.delete(doc)
        
        # Delete compliance records
        compliance_records = ComplianceRecord.query.filter_by(vehicle_id=vehicle.id).all()
        for record in compliance_records:
            db.session.delete(record)
        
        # Finally delete the vehicle
        db.session.delete(vehicle)
        db.session.commit()
        
        flash('Vehicle deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting vehicle. Please try again.', 'error')
    
    return redirect(url_for('user.vehicles'))

@user_bp.route('/vehicle/<int:vehicle_id>')
@login_required
def vehicle_details(vehicle_id):
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first_or_404()
    
    # Get compliance history for this vehicle
    compliance_history = ComplianceRecord.query.filter_by(vehicle_id=vehicle.id).order_by(ComplianceRecord.created_at.desc()).all()
    
    # Get documents for this vehicle
    documents = Document.query.filter_by(vehicle_id=vehicle.id).all()
    
    return render_template('user/vehicle_details.html', 
                          vehicle=vehicle, 
                          compliance_history=compliance_history,
                          documents=documents)

@user_bp.route('/notifications')
@login_required
def notifications():
    if current_user.role != 'vehicle_owner':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Mark all as read
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    
    return render_template('user/notifications.html', notifications=notifications)

@user_bp.route('/documents')
@login_required
def documents():
    if current_user.role != 'vehicle_owner':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    user_documents = Document.query.filter_by(user_id=current_user.id).all()
    return render_template('user/documents.html', documents=user_documents)

@user_bp.route('/document/upload', methods=['POST'])
@login_required
def upload_document():
    if 'document_file' not in request.files:
        flash('No file selected!', 'error')
        return redirect(url_for('user.documents'))
    
    file = request.files['document_file']
    if file.filename == '':
        flash('No file selected!', 'error')
        return redirect(url_for('user.documents'))
    
    document_type = request.form.get('document_type')
    vehicle_id = request.form.get('vehicle_id')
    notes = request.form.get('notes', '')
    
    if not document_type:
        flash('Document type is required!', 'error')
        return redirect(url_for('user.documents'))
    
    if file and allowed_file(file.filename):
        try:
            from werkzeug.utils import secure_filename
            import os
            
            # Validate vehicle if provided
            if vehicle_id:
                vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first()
                if not vehicle:
                    flash('Invalid vehicle selection!', 'error')
                    return redirect(url_for('user.documents'))
            else:
                vehicle = None
            
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join('app', 'uploads', 'documents')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_dir, f"{current_user.id}_{filename}")
            file.save(file_path)
            
            # Create document record
            document = Document(
                user_id=current_user.id,
                vehicle_id=vehicle.id if vehicle else None,
                document_type=document_type,
                document_name=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                notes=notes
            )
            
            db.session.add(document)
            db.session.commit()
            
            flash('Document uploaded successfully!', 'success')
        except Exception as e:
            flash('Error uploading document. Please try again.', 'error')
    else:
        flash('Invalid file type. Only PDF, JPG, PNG, and DOC files are allowed.', 'error')
    
    return redirect(url_for('user.documents'))

def allowed_file(filename):
    """Check if file type is allowed"""
    allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@user_bp.route('/compliance-history')
@login_required
def compliance_history():
    if current_user.role != 'vehicle_owner':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get compliance records for all user's vehicles
    user_vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    vehicle_ids = [v.id for v in user_vehicles]
    
    compliance_records = ComplianceRecord.query.filter(
        ComplianceRecord.vehicle_id.in_(vehicle_ids)
    ).order_by(ComplianceRecord.created_at.desc()).all()
    
    return render_template('user/compliance_history.html', compliance_records=compliance_records)

@user_bp.route('/qr/<int:vehicle_id>')
@login_required
def generate_qr(vehicle_id):
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=current_user.id).first_or_404()
    
    # Get the QR code for this vehicle
    qr_code = QRCode.query.filter_by(vehicle_id=vehicle.id).first()
    
    if not qr_code:
        # Generate new QR code if it doesn't exist
        qr_content = generate_qr_content(vehicle.id, vehicle.vehicle_number, vehicle.cng_expiry_date)
        
        # Create QR code image
        qr_img = qrcode.make(qr_content)
        qr_filename = f"qr_{vehicle.id}_{vehicle.vehicle_number.replace(' ', '_')}.png"
        qr_path = os.path.join('app', 'static', 'qr_codes', qr_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(qr_path), exist_ok=True)
        
        qr_img.save(qr_path)
        
        # Save QR code record to database
        qr_code = QRCode(
            vehicle_id=vehicle.id,
            qr_code_path=qr_path,
            qr_content=qr_content
        )
        db.session.add(qr_code)
        db.session.commit()
    
    return render_template('user/qr_code.html', vehicle=vehicle, qr_code=qr_code)


@user_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_notifications_read():
    if current_user.role != 'vehicle_owner':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
        for notification in notifications:
            notification.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error marking notifications as read'}), 500


@user_bp.route('/notifications/clear-all', methods=['POST'])
@login_required
def clear_notifications():
    if current_user.role != 'vehicle_owner':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        notifications = Notification.query.filter_by(user_id=current_user.id).all()
        for notification in notifications:
            db.session.delete(notification)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error clearing notifications'}), 500