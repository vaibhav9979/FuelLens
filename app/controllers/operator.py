from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Vehicle, ComplianceRecord, FuelStation, StationEmployee
from app.utils.helpers import validate_vehicle_number, calculate_compliance_status, generate_qr_content
import qrcode
import json
from datetime import datetime

operator_bp = Blueprint('operator', __name__)

@operator_bp.route('/dashboard')
@login_required
def dashboard():
    # Only allow station operator users to access this dashboard
    if current_user.role != 'station_operator':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        flash('You are not assigned to any fuel station. Please contact your administrator.', 'warning')
        return redirect(url_for('main.index'))
    
    station = station_employee.station
    
    # Check if the station is approved
    if not station.is_approved:
        flash('Your fuel station has not been approved by the admin yet. Access is restricted until approval.', 'warning')
        return redirect(url_for('main.index'))
    
    # Get recent compliance checks at this station
    recent_checks = ComplianceRecord.query.filter_by(station_id=station.id).order_by(ComplianceRecord.created_at.desc()).limit(10).all()
    
    return render_template('operator/dashboard.html', station=station, recent_checks=recent_checks)

@operator_bp.route('/compliance-check', methods=['GET', 'POST'])
@login_required
def compliance_check():
    if current_user.role != 'station_operator':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        flash('You are not assigned to any fuel station. Please contact your administrator.', 'warning')
        return redirect(url_for('main.index'))
    
    station = station_employee.station
    
    # Check if the station is approved
    if not station.is_approved:
        flash('Your fuel station has not been approved by the admin yet. Access is restricted until approval.', 'warning')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number', '').strip().upper()
        check_type = request.form.get('check_type', 'manual')  # camera, qr, manual
        notes = request.form.get('notes', '')
        
        # Validate vehicle number only for manual entries, skip for QR/camera scans
        if check_type in ['manual', 'camera'] and not validate_vehicle_number(vehicle_number):
            flash('Invalid vehicle number format!', 'error')
            return render_template('operator/compliance_check.html', station=station)
        
        # Find vehicle in database
        vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number).first()
        if not vehicle:
            flash(f'Vehicle {vehicle_number} not found in the system!', 'error')
            return render_template('operator/compliance_check.html', station=station)
        
        # Calculate compliance status
        compliance_status = vehicle.calculate_compliance_status()
        
        # Create compliance record
        compliance_record = ComplianceRecord(
            vehicle_id=vehicle.id,
            station_id=station.id,
            checker_id=current_user.id,
            check_type=check_type,
            compliance_status=compliance_status,
            notes=notes
        )
        
        db.session.add(compliance_record)
        db.session.commit()
        
        # Update station load status based on recent activity
        update_station_load(station)
        
        flash(f'Compliance check completed. Status: {compliance_status.upper()}', 'success')
        return redirect(url_for('operator.dashboard'))
    
    return render_template('operator/scan.html', station=station)

@operator_bp.route('/qr-scan', methods=['POST'])
@login_required
def qr_scan():
    if current_user.role != 'station_operator':
        return jsonify({'error': 'Access denied'}), 403
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        return jsonify({'error': 'You are not assigned to any fuel station. Please contact your administrator.'}), 400
    
    station = station_employee.station
    
    # Check if the station is approved
    if not station.is_approved:
        return jsonify({'error': 'Your fuel station has not been approved by the admin yet. Access is restricted until approval.'}), 400
    
    qr_data = request.form.get('qr_data', '')
    
    try:
        # Parse QR data
        qr_content = json.loads(qr_data)
        vehicle_id = qr_content.get('vehicle_id')
        
        # Get vehicle from database
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({'error': 'Vehicle not found in the system'}), 404
        
        # Calculate compliance status
        compliance_status = vehicle.calculate_compliance_status()
        
        # Return vehicle info without creating compliance record yet
        # This allows the frontend to display the info and then submit compliance check
        return jsonify({
            'status': 'success',
            'vehicle': {
                'id': vehicle.id,
                'number': vehicle.vehicle_number,
                'owner': vehicle.owner_name,
                'type': vehicle.vehicle_type,
                'compliance_status': compliance_status
            }
        })
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid QR code data'}), 400
    except Exception as e:
        return jsonify({'error': 'Error processing QR code'}), 500

def update_station_load(station):
    """Update station load based on recent activity"""
    from datetime import datetime, timedelta
    
    # Count checks in the last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_checks = ComplianceRecord.query.filter(
        ComplianceRecord.station_id == station.id,
        ComplianceRecord.created_at >= one_hour_ago
    ).count()
    
    # Update load status based on check count
    if recent_checks >= 10:
        station.live_load = 'busy'
    elif recent_checks >= 5:
        station.live_load = 'normal'
    else:
        station.live_load = 'free'
    
    station.updated_at = datetime.utcnow()
    db.session.commit()

# Route for operators to add vehicles to the system
@operator_bp.route('/add-vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if current_user.role != 'station_operator':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        flash('You are not assigned to any fuel station. Please contact your administrator.', 'warning')
        return redirect(url_for('main.index'))
    
    station = station_employee.station
    
    # Check if the station is approved
    if not station.is_approved:
        flash('Your fuel station has not been approved by the admin yet. Access is restricted until approval.', 'warning')
        return redirect(url_for('main.index'))
    
    # Get vehicle number from query parameter if available
    vehicle_number = request.args.get('vehicle_number', '').strip().upper()
    
    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number', '').strip().upper()
        owner_name = request.form.get('owner_name', '').strip()
        vehicle_type = request.form.get('vehicle_type', 'car')
        fuel_type = request.form.get('fuel_type', 'petrol')
        cng_expiry_date = request.form.get('cng_expiry_date')
        insurance_expiry_date = request.form.get('insurance_expiry_date')
        pollution_expiry_date = request.form.get('pollution_expiry_date')
        
        # Validation
        if not all([vehicle_number, owner_name, vehicle_type]):
            flash('Vehicle number, owner name, and vehicle type are required!', 'error')
            return render_template('operator/add_vehicle.html', prefill_vehicle_number=vehicle_number)
        
        # Check if vehicle number already exists
        existing_vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number).first()
        if existing_vehicle:
            flash('Vehicle number already exists in the system!', 'error')
            return render_template('operator/add_vehicle.html', prefill_vehicle_number=vehicle_number)
        
        # Convert dates if provided
        from datetime import datetime
        cng_expiry = datetime.strptime(cng_expiry_date, '%Y-%m-%d').date() if cng_expiry_date else None
        insurance_expiry = datetime.strptime(insurance_expiry_date, '%Y-%m-%d').date() if insurance_expiry_date else None
        pollution_expiry = datetime.strptime(pollution_expiry_date, '%Y-%m-%d').date() if pollution_expiry_date else None
        
        try:
            # Create new vehicle
            vehicle = Vehicle(
                vehicle_number=vehicle_number,
                owner_name=owner_name,
                vehicle_type=vehicle_type,
                fuel_type=fuel_type,
                cng_expiry_date=cng_expiry,
                insurance_expiry_date=insurance_expiry,
                pollution_expiry_date=pollution_expiry,
                last_compliance_date=datetime.utcnow().date()
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
            return redirect(url_for('operator.compliance_check'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding vehicle. Please try again.', 'error')
    
    return render_template('operator/add_vehicle.html', prefill_vehicle_number=vehicle_number)


@operator_bp.route('/station-status')
@login_required
def station_status():
    if current_user.role != 'station_operator':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        flash('You are not assigned to any fuel station. Please contact your administrator.', 'warning')
        return redirect(url_for('main.index'))
    
    station = station_employee.station
    
    # Check if the station is approved
    if not station.is_approved:
        flash('Your fuel station has not been approved by the admin yet. Access is restricted until approval.', 'warning')
        return redirect(url_for('main.index'))
    
    # Get recent compliance checks
    recent_checks = ComplianceRecord.query.filter_by(station_id=station.id).order_by(ComplianceRecord.created_at.desc()).limit(10).all()
    
    return render_template('operator/station_status.html', station=station, recent_checks=recent_checks)

@operator_bp.route('/update-station-status', methods=['POST'])
@login_required
def update_station_status():
    if current_user.role != 'station_operator':
        return jsonify({'error': 'Access denied'}), 403
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        return jsonify({'error': 'You are not assigned to any fuel station. Please contact your administrator.'}), 400
    
    station = station_employee.station
    
    # Check if the station is approved
    if not station.is_approved:
        return jsonify({'error': 'Your fuel station has not been approved by the admin yet. Access is restricted until approval.'}), 400
    
    is_open = request.form.get('is_open', type=bool)
    live_load = request.form.get('live_load', 'normal')
    fuel_availability = request.form.get('fuel_availability', 'available')
    
    try:
        station.is_open = is_open
        station.live_load = live_load
        station.fuel_availability = fuel_availability
        station.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Station status updated successfully!', 'success')
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error updating station status'}), 500

@operator_bp.route('/search-vehicle')
@login_required
def search_vehicle():
    if current_user.role != 'station_operator':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    query = request.args.get('q', '').strip().upper()
    
    if query:
        vehicles = Vehicle.query.filter(Vehicle.vehicle_number.like(f'%{query}%')).limit(10).all()
    else:
        vehicles = []
    
    return render_template('operator/search_results.html', vehicles=vehicles, query=query)

@operator_bp.route('/vehicle-history/<int:vehicle_id>')
@login_required
def vehicle_history(vehicle_id):
    if current_user.role != 'station_operator':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        flash('You are not assigned to any fuel station. Please contact your administrator.', 'warning')
        return redirect(url_for('main.index'))
    
    station = station_employee.station
    
    # Get vehicle and its compliance history
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    compliance_history = ComplianceRecord.query.filter_by(vehicle_id=vehicle_id).order_by(ComplianceRecord.created_at.desc()).all()
    
    return render_template('operator/vehicle_history.html', 
                          vehicle=vehicle, 
                          compliance_history=compliance_history,
                          station=station)


@operator_bp.route('/history')
@login_required
def history():
    if current_user.role != 'station_operator':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        flash('You are not assigned to any fuel station. Please contact your administrator.', 'warning')
        return redirect(url_for('main.index'))
    
    station = station_employee.station
    
    # Get compliance history for this station
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = ComplianceRecord.query.filter_by(station_id=station.id).join(ComplianceRecord.vehicle).join(ComplianceRecord.checker)
    if status_filter:
        query = query.filter(ComplianceRecord.compliance_status == status_filter)
    
    compliance_records = query.order_by(ComplianceRecord.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('operator/history.html', compliance_records=compliance_records, status_filter=status_filter)


@operator_bp.route('/camera-scan', methods=['POST'])
@login_required
def camera_scan():
    if current_user.role != 'station_operator':
        return jsonify({'error': 'Access denied'}), 403
    
    # Get the station assigned to this operator
    station_employee = StationEmployee.query.filter_by(employee_id=current_user.id, is_active=True).first()
    if not station_employee:
        return jsonify({'error': 'You are not assigned to any fuel station. Please contact your administrator.'}), 400
    
    # Check if we have an image file uploaded or captured image data
    image_provided = 'image' in request.files and request.files['image'].filename != ''
    captured_image_data = request.form.get('captured_image_data')
    
    if not image_provided and not captured_image_data:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        # Check if we have a captured image data (base64) or file upload
        captured_image_data = request.form.get('captured_image_data')
        
        import os
        import tempfile
        import base64
        from app.utils.plate_detector import PlateDetector
        
        temp_path = None
        
        try:
            if captured_image_data:
                # Handle base64 image data from camera capture
                # Remove data URL prefix if present (e.g., 'data:image/png;base64,')
                if ',' in captured_image_data:
                    header, encoded = captured_image_data.split(',', 1)
                    image_data = base64.b64decode(encoded)
                else:
                    image_data = base64.b64decode(captured_image_data)
                
                # Create a temporary file to save the image
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file.write(image_data)
                    temp_path = temp_file.name
            else:
                # Handle file upload
                image_file = request.files['image']
                
                # Create a temporary file to save the uploaded image
                # Get file extension or default to .jpg
                file_ext = os.path.splitext(image_file.filename)[1]
                if not file_ext:
                    file_ext = '.jpg'  # Default to jpg if no extension
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                    image_file.save(temp_file.name)
                    temp_path = temp_file.name
            
            # Initialize plate detector
            detector = PlateDetector()
            
            # Detect plate from the saved image
            detected_plate = detector.detect_plate_from_image(temp_path)
            
            if detected_plate:
                # Validate if the detected plate exists in the database
                vehicle = detector.validate_plate_in_db(detected_plate)
                if vehicle:
                    # Calculate compliance status
                    compliance_status = vehicle.calculate_compliance_status()
                    
                    return jsonify({
                        'status': 'success',
                        'vehicle_number': detected_plate,
                        'vehicle_exists': True,
                        'message': f'Vehicle found in database: {detected_plate}',
                        'vehicle_details': {
                            'id': vehicle.id,
                            'owner_name': vehicle.owner.get_full_name() if vehicle.owner else 'Unknown',
                            'owner_email': vehicle.owner.email if vehicle.owner else 'N/A',
                            'owner_phone': vehicle.owner.phone if vehicle.owner else 'N/A',
                            'vehicle_type': vehicle.vehicle_type,
                            'fuel_type': vehicle.fuel_type,
                            'cng_expiry_date': vehicle.cng_expiry_date.strftime('%Y-%m-%d') if vehicle.cng_expiry_date else 'N/A',
                            'compliance_status': compliance_status,
                            'last_compliance_date': vehicle.last_compliance_date.strftime('%Y-%m-%d') if vehicle.last_compliance_date else 'N/A',
                            'insurance_expiry': vehicle.insurance_expiry_date.strftime('%Y-%m-%d') if vehicle.insurance_expiry_date else 'N/A',
                            'pollution_expiry': vehicle.pollution_expiry_date.strftime('%Y-%m-%d') if vehicle.pollution_expiry_date else 'N/A'
                        }
                    })
                else:
                    return jsonify({
                        'status': 'success',
                        'vehicle_number': detected_plate,
                        'vehicle_exists': False,
                        'message': f'Vehicle detected: {detected_plate} (not found in database)'
                    })
            else:
                # No plate detected from image, check if manual vehicle number was provided
                manual_vehicle_number = request.form.get('manual_vehicle_number', '').strip().upper()
                if manual_vehicle_number:
                    vehicle = detector.validate_plate_in_db(manual_vehicle_number)
                    if vehicle:
                        # Calculate compliance status
                        compliance_status = vehicle.calculate_compliance_status()
                        
                        return jsonify({
                            'status': 'success',
                            'vehicle_number': manual_vehicle_number,
                            'vehicle_exists': True,
                            'message': f'Vehicle found in database: {manual_vehicle_number}',
                            'vehicle_details': {
                                'id': vehicle.id,
                                'owner_name': vehicle.owner.get_full_name() if vehicle.owner else 'Unknown',
                                'owner_email': vehicle.owner.email if vehicle.owner else 'N/A',
                                'owner_phone': vehicle.owner.phone if vehicle.owner else 'N/A',
                                'vehicle_type': vehicle.vehicle_type,
                                'fuel_type': vehicle.fuel_type,
                                'cng_expiry_date': vehicle.cng_expiry_date.strftime('%Y-%m-%d') if vehicle.cng_expiry_date else 'N/A',
                                'compliance_status': compliance_status,
                                'last_compliance_date': vehicle.last_compliance_date.strftime('%Y-%m-%d') if vehicle.last_compliance_date else 'N/A',
                                'insurance_expiry': vehicle.insurance_expiry_date.strftime('%Y-%m-%d') if vehicle.insurance_expiry_date else 'N/A',
                                'pollution_expiry': vehicle.pollution_expiry_date.strftime('%Y-%m-%d') if vehicle.pollution_expiry_date else 'N/A'
                            }
                        })
                    else:
                        return jsonify({
                            'status': 'success',
                            'vehicle_number': manual_vehicle_number,
                            'vehicle_exists': False,
                            'message': f'Vehicle manually entered: {manual_vehicle_number} (not found in database)'
                        })
                else:
                    # No plate detected and no manual entry, return error
                    return jsonify({
                        'status': 'error',
                        'error': 'Could not detect vehicle number from image'
                    }), 400
        finally:
            # Clean up the temporary file if it was created
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        print(f'Error in camera scan: {e}')
        return jsonify({'error': 'Error processing image'}), 500