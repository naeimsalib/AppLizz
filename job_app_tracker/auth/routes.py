from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from job_app_tracker.models.user import User
from job_app_tracker.auth.forms import LoginForm, RegistrationForm
from werkzeug.security import generate_password_hash
from bson import ObjectId
from job_app_tracker.config.mongodb import mongo

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_email(form.email.data)
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.dashboard'))
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.get_by_email(form.email.data):
            flash('Email already registered', 'error')
            return render_template('auth/register.html', form=form)
        
        user = User.create_user(
            email=form.email.data,
            password=form.password.data,
            name=form.name.data
        )
        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/profile', methods=['POST'])
@login_required
def profile():
    """Update user profile information"""
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    # Update user information
    mongo.db.users.update_one(
        {'_id': ObjectId(current_user.id)},
        {'$set': {
            'first_name': first_name,
            'last_name': last_name
        }}
    )
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('main.settings'))

@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Verify current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('main.settings'))
    
    # Verify new password
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('main.settings'))
    
    # Update password
    mongo.db.users.update_one(
        {'_id': ObjectId(current_user.id)},
        {'$set': {'password_hash': generate_password_hash(new_password)}}
    )
    
    flash('Password updated successfully!', 'success')
    return redirect(url_for('main.settings'))

@auth.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    confirm_delete = request.form.get('confirm_delete')
    
    if confirm_delete != 'DELETE':
        flash('Please type DELETE to confirm account deletion', 'error')
        return redirect(url_for('main.settings'))
    
    # Delete user's job applications
    mongo.db.applications.delete_many({'user_id': current_user.id})
    
    # Delete user account
    mongo.db.users.delete_one({'_id': ObjectId(current_user.id)})
    
    # Log out the user
    logout_user()
    
    flash('Your account has been permanently deleted', 'success')
    return redirect(url_for('main.index')) 