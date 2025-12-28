from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Vehicle, ComplianceRecord, FuelStation, Document, StationRating, Notification, StationEmployee
from app.utils.helpers import send_notification
from app.utils.reporting import ReportingService
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Only allow admin users to access this dashboard
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get statistics
    total_users = User.query.count()
    total_vehicles = Vehicle.query.count()
    total_stations = FuelStation.query.count()
    total_compliance_checks = ComplianceRecord.query.count()
    pending_stations = FuelStation.query.filter_by(is_approved=False, is_active=True).count()  # Unapproved but active stations
    
    # Get recent activities
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).limit(5).all()
    recent_compliance = ComplianceRecord.query.order_by(ComplianceRecord.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                          total_users=total_users,
                          total_vehicles=total_vehicles,
                          total_stations=total_stations,
                          total_compliance_checks=total_compliance_checks,
                          pending_stations=pending_stations,
                          recent_users=recent_users,
                          recent_vehicles=recent_vehicles,
                          recent_compliance=recent_compliance)

@admin_bp.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '')
    
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    users = query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/users.html', users=users, role_filter=role_filter)

@admin_bp.route('/user/<int:user_id>')
@login_required
def user_details(user_id):
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(user_id)
    vehicles = Vehicle.query.filter_by(user_id=user_id).all()
    
    return render_template('admin/user_details.html', user=user, vehicles=vehicles)

@admin_bp.route('/user/<int:user_id>/toggle-active', methods=['POST'])
@login_required
def toggle_user_active(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    try:
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User {status} successfully!', 'success')
        
        # Send notification to user
        send_notification(
            user_id=user.id,
            title=f'Account {status}',
            message=f'Your account has been {status} by an administrator.',
            notification_type='system'
        )
        
        return jsonify({'success': True, 'is_active': user.is_active})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error updating user status'}), 500

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'error': 'You cannot delete your own account'}), 400
    
    try:
        # Delete related records first
        # Delete vehicles and related records
        vehicles = Vehicle.query.filter_by(user_id=user.id).all()
        for vehicle in vehicles:
            # Delete QR codes
            from app.models import QRCode
            qr_codes = QRCode.query.filter_by(vehicle_id=vehicle.id).all()
            for qr in qr_codes:
                import os
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
        
        # Delete user's documents
        user_docs = Document.query.filter_by(user_id=user.id).all()
        for doc in user_docs:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
            db.session.delete(doc)
        
        # Delete user's notifications
        notifications = Notification.query.filter_by(user_id=user.id).all()
        for notification in notifications:
            db.session.delete(notification)
        
        # Delete station employee records
        from app.models import StationEmployee
        station_employees = StationEmployee.query.filter_by(employee_id=user.id).all()
        for emp in station_employees:
            db.session.delete(emp)
        
        # Finally delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash('User deleted successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error deleting user'}), 500

@admin_bp.route('/vehicles')
@login_required
def vehicles():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    compliance_filter = request.args.get('compliance', '')
    
    query = Vehicle.query.join(User)
    if compliance_filter:
        query = query.filter(Vehicle.compliance_status == compliance_filter)
    
    vehicles = query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/vehicles.html', vehicles=vehicles, status_filter=compliance_filter)

@admin_bp.route('/vehicle/<int:vehicle_id>')
@login_required
def vehicle_details(vehicle_id):
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    compliance_history = ComplianceRecord.query.filter_by(vehicle_id=vehicle_id).order_by(ComplianceRecord.created_at.desc()).all()
    
    return render_template('admin/vehicle_details.html', vehicle=vehicle, compliance_history=compliance_history)

@admin_bp.route('/stations')
@login_required
def stations():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    approval_filter = request.args.get('approval', '')  # 'approved', 'pending', 'rejected'
    
    query = FuelStation.query
    
    # Apply approval filter
    if approval_filter == 'approved':
        query = query.filter(FuelStation.is_approved == True)
    elif approval_filter == 'pending':
        query = query.filter(FuelStation.is_approved == False, FuelStation.is_active == True)
    elif approval_filter == 'rejected':
        query = query.filter(FuelStation.is_approved == False, FuelStation.is_active == False)
    
    # Apply status filter (active/inactive)
    if status_filter:
        if status_filter == 'active':
            query = query.filter(FuelStation.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(FuelStation.is_active == False)
    
    stations = query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/stations.html', stations=stations, status_filter=status_filter, approval_filter=approval_filter)

@admin_bp.route('/station/<int:station_id>')
@login_required
def station_details(station_id):
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    station = FuelStation.query.get_or_404(station_id)
    employees = User.query.join(StationEmployee).filter(StationEmployee.station_id == station_id, StationEmployee.is_active == True).all()
    compliance_records = ComplianceRecord.query.filter_by(station_id=station_id).order_by(ComplianceRecord.created_at.desc()).limit(10).all()
    ratings = StationRating.query.filter_by(station_id=station_id).order_by(StationRating.created_at.desc()).limit(10).all()
    
    return render_template('admin/station_details.html', 
                          station=station, 
                          employees=employees,
                          compliance_records=compliance_records,
                          ratings=ratings)

@admin_bp.route('/compliance')
@login_required
def compliance():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = ComplianceRecord.query.join(ComplianceRecord.vehicle).join(ComplianceRecord.station)
    
    if status_filter:
        query = query.filter(ComplianceRecord.compliance_status == status_filter)
    
    compliance_records = query.order_by(ComplianceRecord.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/compliance.html', 
                          compliance_records=compliance_records, 
                          status_filter=status_filter)

@admin_bp.route('/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    reporting_service = ReportingService()
    
    # Get all required statistics
    user_stats = reporting_service.get_user_statistics()
    vehicle_stats = reporting_service.get_vehicle_statistics()
    compliance_stats = reporting_service.get_compliance_statistics()
    station_stats = reporting_service.get_station_statistics()
    daily_checks = reporting_service.get_daily_compliance_trends()
    station_compliance = reporting_service.get_top_stations_by_compliance()
    vehicle_types = reporting_service.get_compliance_by_vehicle_type()
    
    # Combine all stats
    all_stats = {**user_stats, **vehicle_stats, **compliance_stats, **station_stats}
    
    return render_template('admin/reports.html',
                          compliance_stats=all_stats,
                          station_compliance=station_compliance,
                          daily_checks=daily_checks,
                          vehicle_types=vehicle_types)

@admin_bp.route('/notifications')
@login_required
def notifications():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.join(Notification.user).order_by(Notification.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/notifications.html', notifications=notifications)

@admin_bp.route('/send-notification', methods=['POST'])
@login_required
def send_notification_route():
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user_id = request.form.get('user_id', type=int)
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    notification_type = request.form.get('type', 'system')
    
    if not all([user_id, title, message]):
        return jsonify({'error': 'All fields are required'}), 400
    
    try:
        send_notification(user_id, title, message, notification_type)
        flash('Notification sent successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'Error sending notification'}), 500

# Add the operators route before system settings
@admin_bp.route('/operators')
@login_required
def operators():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = User.query.filter_by(role='station_operator')
    if status_filter:
        is_active = status_filter == 'active'
        query = query.filter_by(is_active=is_active)
    
    operators = query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/operators.html', operators=operators, status_filter=status_filter)


@admin_bp.route('/operator/<int:operator_id>/deactivate', methods=['POST'])
@login_required
def deactivate_operator(operator_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.filter_by(id=operator_id, role='station_operator').first_or_404()
    
    try:
        user.is_active = False
        db.session.commit()
        
        # Send notification to operator
        send_notification(
            user_id=user.id,
            title='Account Deactivated',
            message='Your account has been deactivated by an administrator.',
            notification_type='system'
        )
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error deactivating operator'}), 500


@admin_bp.route('/operator/<int:operator_id>/activate', methods=['POST'])
@login_required
def activate_operator(operator_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.filter_by(id=operator_id, role='station_operator').first_or_404()
    
    try:
        user.is_active = True
        db.session.commit()
        
        # Send notification to operator
        send_notification(
            user_id=user.id,
            title='Account Activated',
            message='Your account has been activated by an administrator.',
            notification_type='system'
        )
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error activating operator'}), 500


@admin_bp.route('/station-assignments')
@login_required
def station_assignments():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    # Get all operators and stations
    operators = User.query.filter_by(role='station_operator').all()
    stations = FuelStation.query.all()
    
    # Get current assignments
    assignments = StationEmployee.query.all()
    
    return render_template('admin/station_assignments.html', 
                          operators=operators, 
                          stations=stations, 
                          assignments=assignments)


@admin_bp.route('/assign-operator', methods=['POST'])
@login_required
def assign_operator():
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    operator_id = request.form.get('operator_id', type=int)
    station_id = request.form.get('station_id', type=int)
    role = request.form.get('role', 'operator')
    
    if not all([operator_id, station_id]):
        return jsonify({'error': 'Operator and station are required'}), 400
    
    try:
        # Validate that operator exists and is a station operator
        operator = User.query.filter_by(id=operator_id, role='station_operator').first()
        if not operator:
            return jsonify({'error': 'Invalid operator selected'}), 400
        
        # Validate that station exists
        station = FuelStation.query.get(station_id)
        if not station:
            return jsonify({'error': 'Invalid station selected'}), 400
        
        # Check if assignment already exists
        existing_assignment = StationEmployee.query.filter_by(
            employee_id=operator_id, 
            station_id=station_id
        ).first()
        
        if existing_assignment:
            # Update existing assignment
            existing_assignment.is_active = True
            existing_assignment.role = role
        else:
            # Create new assignment
            assignment = StationEmployee(
                station_id=station_id,
                employee_id=operator_id,
                role=role,
                is_active=True
            )
            db.session.add(assignment)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Operator assigned to station successfully!'})
    except Exception as e:
        db.session.rollback()
        print(f'Error assigning operator to station: {str(e)}')  # For debugging
        return jsonify({'error': f'Error assigning operator to station: {str(e)}'}), 500


@admin_bp.route('/remove-assignment/<int:assignment_id>', methods=['POST'])
@login_required
def remove_assignment(assignment_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        assignment = StationEmployee.query.get_or_404(assignment_id)
        assignment.is_active = False  # Soft delete
        db.session.commit()
        return jsonify({'success': True, 'message': 'Operator assignment removed successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error removing assignment'}), 500


@admin_bp.route('/pending-stations')
@login_required
def pending_stations():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    
    # Get stations that are not approved
    stations = FuelStation.query.filter_by(is_approved=False).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/pending_stations.html', stations=stations)


@admin_bp.route('/approve-station/<int:station_id>', methods=['POST'])
@login_required
def approve_station(station_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    station = FuelStation.query.get_or_404(station_id)
    
    try:
        notes = request.form.get('approval_notes', '').strip()
        station.approve_station(admin_user_id=current_user.id, notes=notes)
        db.session.commit()
        
        flash(f'Station "{station.name}" approved successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error approving station'}), 500


@admin_bp.route('/reject-station/<int:station_id>', methods=['POST'])
@login_required
def reject_station(station_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    station = FuelStation.query.get_or_404(station_id)
    
    try:
        # For rejection, we can deactivate the station
        station.is_active = False
        station.is_approved = False
        station.approval_notes = f"Rejected by admin: {request.form.get('rejection_reason', 'No reason provided')}"
        db.session.commit()
        
        flash(f'Station "{station.name}" rejected successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error rejecting station'}), 500


@admin_bp.route('/documents')
@login_required
def documents():
    # Check if user is an admin
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    
    query = Document.query.join(Document.owner)
    
    if status_filter:
        if status_filter == 'verified':
            query = query.filter(Document.is_verified == True)
        elif status_filter == 'pending':
            query = query.filter(Document.is_verified == False)
    
    if type_filter:
        query = query.filter(Document.document_type == type_filter)
    
    documents = query.order_by(Document.uploaded_at.desc()).paginate(page=page, per_page=10, error_out=False)
    
    from datetime import date
    return render_template('admin/documents.html', documents=documents, status_filter=status_filter, type_filter=type_filter, today=date.today)


@admin_bp.route('/verify-document/<int:document_id>', methods=['POST'])
@login_required
def verify_document(document_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    document = Document.query.get_or_404(document_id)
    
    try:
        action = request.form.get('action')  # 'verify' or 'reject'
        notes = request.form.get('notes', '').strip()
        
        if action == 'verify':
            document.is_verified = True
            document.notes = notes if notes else document.notes
            message = 'Document verified successfully!'
        elif action == 'reject':
            document.is_verified = False
            document.notes = notes if notes else document.notes
            message = 'Document rejected!'
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        db.session.commit()
        
        # Send notification to document owner
        from app.utils.helpers import send_notification
        send_notification(
            user_id=document.user_id,
            title=f'Document {"Verified" if action == "verify" else "Rejected"}',
            message=f'Your document "{document.document_name}" has been {"verified" if action == "verify" else "rejected"} by an administrator.',
            notification_type='system'
        )
        
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error processing document'}), 500


@admin_bp.route('/system-settings')
@login_required
def system_settings():
    if current_user.role != 'admin':
        flash('Access denied. You are not authorized to access this page.', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('admin/system_settings.html')