from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, mail
from app.models import User
from app.utils.helpers import send_email
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email').strip().lower()
        first_name = request.form.get('first_name').strip()
        last_name = request.form.get('last_name').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'vehicle_owner')  # Default to vehicle_owner
        
        # Validation
        if not all([email, first_name, last_name, password]):
            flash('All fields are required!', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template('auth/register.html')
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash('Invalid email format!', 'error')
            return render_template('auth/register.html')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        try:
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        remember_me = bool(request.form.get('remember_me'))
        
        if not all([email, password]):
            flash('Email and password are required!', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=remember_me)
                
                # Redirect based on user role
                if user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user.role == 'station_operator':
                    return redirect(url_for('operator.dashboard'))
                else:  # vehicle_owner
                    return redirect(url_for('user.dashboard'))
            else:
                flash('Account is deactivated. Please contact support.', 'error')
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        
        if not email:
            flash('Email is required!', 'error')
            return render_template('auth/forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = user.get_reset_token()
            
            # Send reset email
            try:
                send_email(
                    subject="Password Reset Request",
                    recipients=[user.email],
                    body=f"""To reset your password, visit the following link:
{url_for('auth.reset_password', token=token, _external=True)}

If you did not make this request, please ignore this email.
This link will expire in 10 minutes."""
                )
                flash('Password reset link has been sent to your email!', 'success')
            except Exception as e:
                flash('Error sending reset email. Please try again.', 'error')
        else:
            # Don't reveal if email exists to prevent enumeration
            flash('If email exists, a reset link has been sent to your email!', 'info')
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    
    if not user:
        flash('Invalid or expired token!', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        try:
            user.set_password(password)
            db.session.commit()
            flash('Your password has been updated! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating password. Please try again.', 'error')
    
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    first_name = request.form.get('first_name').strip()
    last_name = request.form.get('last_name').strip()
    phone = request.form.get('phone', '').strip()
    
    if not all([first_name, last_name]):
        flash('First name and last name are required!', 'error')
        return redirect(url_for('auth.profile'))
    
    try:
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.phone = phone
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating profile. Please try again.', 'error')
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        flash('All password fields are required!', 'error')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match!', 'error')
        return redirect(url_for('auth.profile'))
    
    if len(new_password) < 6:
        flash('New password must be at least 6 characters long!', 'error')
        return redirect(url_for('auth.profile'))
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect!', 'error')
        return redirect(url_for('auth.profile'))
    
    try:
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error changing password. Please try again.', 'error')
    
    return redirect(url_for('auth.profile'))