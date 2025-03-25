from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from job_app_tracker.models.user import User
from werkzeug.security import check_password_hash
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# Simple login form class
class LoginForm:
    def __init__(self, request=None):
        self.email = type('obj', (object,), {'data': '', 'errors': []})
        self.password = type('obj', (object,), {'data': '', 'errors': []})
        self.remember = type('obj', (object,), {'data': False})
        self.submit = type('obj', (object,), {'label': 'Sign In'})
        
        if request and request.method == 'POST':
            self.email.data = request.form.get('email', '')
            self.password.data = request.form.get('password', '')
            self.remember.data = 'remember' in request.form
    
    def hidden_tag(self):
        return ''
    
    def validate_on_submit(self):
        valid = True
        if not self.email.data:
            self.email.errors.append('Email is required')
            valid = False
        if not self.password.data:
            self.password.errors.append('Password is required')
            valid = False
        return valid

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm(request)
    
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        remember = form.remember.data
        
        # Get user by email
        user = User.get_by_email(email)
        
        # Check if user exists and password is correct
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Logged in successfully!', 'success')
            
            # Redirect to dashboard
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        # Validate input
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
        
        # Create user
        success, result = User.create_user(username, email, password, first_name, last_name)
        
        if success:
            # User created successfully
            user = result
            login_user(user)
            flash('Registration successful!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            # Failed to create user
            flash(result, 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile route"""
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        success, message = current_user.update_profile(
            first_name=first_name,
            last_name=last_name
        )
        
        if success:
            flash('Profile updated successfully!', 'success')
        else:
            flash(message, 'error')
            
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password route"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.change_password'))
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('auth.change_password'))
        
        # Verify current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('auth.change_password'))
        
        # Update password
        current_user.update_password(new_password)
        flash('Password updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html') 