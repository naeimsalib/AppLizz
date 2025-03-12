from flask import Blueprint, redirect, url_for, request, flash, render_template, session, jsonify
from flask_login import login_required, current_user
import os
import json
from job_app_tracker.services.email_service import EmailService
from job_app_tracker.models.user import User
from job_app_tracker.config.mongodb import mongo
from bson.objectid import ObjectId
from datetime import datetime

email_bp = Blueprint('email', __name__)

@email_bp.route('/connect/gmail')
@login_required
def connect_gmail():
    """Connect Gmail account"""
    auth_url = EmailService.get_gmail_auth_url(str(current_user.id))
    return redirect(auth_url)

@email_bp.route('/connect/yahoo-imap', methods=['GET', 'POST'])
@login_required
def connect_yahoo_imap():
    """Connect Yahoo Mail account using IMAP"""
    if request.method == 'POST':
        yahoo_email = request.form.get('yahoo_email')
        app_password = request.form.get('app_password')
        
        if not yahoo_email or not app_password:
            flash('Please provide both email and app password', 'danger')
            return redirect(url_for('email.connect_yahoo_imap'))
        
        success, result = EmailService.connect_yahoo_imap(str(current_user.id), yahoo_email, app_password)
        
        if success:
            flash('Yahoo Mail connected successfully!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash(f'Failed to connect Yahoo Mail: {result}', 'danger')
            return redirect(url_for('email.connect_yahoo_imap'))
    
    return render_template('email/yahoo_connect.html')

@email_bp.route('/callback/gmail')
def gmail_callback():
    """Handle Gmail OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        flash('Authentication failed', 'danger')
        return redirect(url_for('main.dashboard'))
    
    success, user = EmailService.handle_gmail_callback(code, state)
    
    if success:
        flash('Gmail connected successfully!', 'success')
    else:
        flash('Failed to connect Gmail', 'danger')
    
    return redirect(url_for('main.dashboard'))

@email_bp.route('/scan')
@login_required
def scan_emails():
    """Scan emails for job applications"""
    if not current_user.email_connected:
        flash('Please connect your email first', 'warning')
        return redirect(url_for('main.dashboard'))
    
    success, message = EmailService.scan_emails(current_user)
    
    if success:
        flash(message, 'success')
    else:
        flash(f'Failed to scan emails: {message}', 'danger')
    
    return redirect(url_for('main.dashboard'))

@email_bp.route('/suggestions')
@login_required
def view_suggestions():
    """View email suggestions"""
    # Get unprocessed suggestions
    suggestions = mongo.db.email_suggestions.find_one({
        'user_id': str(current_user.id),
        'processed': False
    })
    
    if not suggestions:
        flash('No suggestions found', 'info')
        return redirect(url_for('main.dashboard'))
    
    return render_template('email/suggestions.html', suggestions=suggestions)

@email_bp.route('/suggestions/process', methods=['POST'])
@login_required
def process_suggestions():
    """Process email suggestions"""
    suggestion_id = request.form.get('suggestion_id')
    accepted_ids = request.form.getlist('accept')
    
    if not suggestion_id:
        flash('Invalid request', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get suggestion document
    suggestion_doc = mongo.db.email_suggestions.find_one({
        '_id': ObjectId(suggestion_id),
        'user_id': str(current_user.id)
    })
    
    if not suggestion_doc:
        flash('Suggestion not found', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Process accepted suggestions
    for suggestion in suggestion_doc['suggestions']:
        if str(suggestion.get('application_id', '')) in accepted_ids or \
           f"new_{suggestion_doc['suggestions'].index(suggestion)}" in accepted_ids:
            
            if suggestion['type'] == 'update':
                # Update existing application
                mongo.db.applications.update_one(
                    {'_id': ObjectId(suggestion['application_id'])},
                    {'$set': {'status': suggestion['new_status']}}
                )
            elif suggestion['type'] == 'new':
                # Add new application
                new_app = {
                    'user_id': str(current_user.id),
                    'company': suggestion['company'],
                    'position': suggestion['position'] if suggestion['position'] != 'Unknown Position' else '',
                    'status': suggestion['status'],
                    'date_applied': suggestion['date'],
                    'notes': f"Automatically added from email: {suggestion['email_subject']}",
                    'created_at': datetime.utcnow()
                }
                mongo.db.applications.insert_one(new_app)
    
    # Mark suggestion as processed
    mongo.db.email_suggestions.update_one(
        {'_id': ObjectId(suggestion_id)},
        {'$set': {'processed': True}}
    )
    
    flash('Suggestions processed successfully', 'success')
    return redirect(url_for('main.dashboard'))

@email_bp.route('/disconnect')
@login_required
def disconnect_email():
    """Disconnect email account"""
    user = User.get_by_id(str(current_user.id))
    if user:
        user.disconnect_email()
        flash('Email disconnected successfully', 'success')
    else:
        flash('Failed to disconnect email', 'danger')
    
    return redirect(url_for('main.dashboard'))

@email_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def email_settings():
    """Email settings"""
    if request.method == 'POST':
        require_approval = request.form.get('require_approval') == 'on'
        scan_frequency = request.form.get('scan_frequency', 'manual')
        
        user = User.get_by_id(str(current_user.id))
        if user:
            settings = user.email_settings or {}
            settings['require_approval'] = require_approval
            settings['scan_frequency'] = scan_frequency
            user.update_email_settings(settings)
            flash('Email settings updated', 'success')
        else:
            flash('Failed to update settings', 'danger')
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('email/settings.html', user=current_user) 