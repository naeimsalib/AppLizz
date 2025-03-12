from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from job_app_tracker.config.mongodb import mongo
from datetime import datetime, timedelta
from bson import ObjectId
from job_app_tracker.services.email_service import EmailService
import os

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main.route('/faq')
def faq():
    return render_template('faq.html')

@main.route('/dashboard')
@login_required
def dashboard():
    # Get all applications for the current user
    applications = list(mongo.db.applications.find({'user_id': str(current_user.id)}))
    
    # Convert ObjectId to string and format dates
    for app in applications:
        app['_id'] = str(app['_id'])
        if isinstance(app.get('date_applied'), str):
            try:
                app['date_applied'] = datetime.strptime(app['date_applied'], '%Y-%m-%d')
            except ValueError:
                app['date_applied'] = datetime.now()
        elif not app.get('date_applied'):
            app['date_applied'] = datetime.now()
    
    # Calculate statistics
    today = datetime.now()
    one_week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    three_weeks_ago = today - timedelta(days=21)
    four_weeks_ago = today - timedelta(days=28)
    
    stats = {
        'total': len(applications),
        'applied': sum(1 for app in applications if app.get('status') == 'Applied'),
        'in_progress': sum(1 for app in applications if app.get('status') == 'In Progress'),
        'interviews': sum(1 for app in applications if app.get('status') == 'Interview'),
        'offers': sum(1 for app in applications if app.get('status') == 'Offer'),
        'rejected': sum(1 for app in applications if app.get('status') == 'Rejected'),
        
        # Applications by time period
        'last_week': sum(1 for app in applications if app.get('date_applied') and app.get('date_applied') >= one_week_ago),
        'two_weeks_ago': sum(1 for app in applications if app.get('date_applied') and two_weeks_ago <= app.get('date_applied') < one_week_ago),
        'three_weeks_ago': sum(1 for app in applications if app.get('date_applied') and three_weeks_ago <= app.get('date_applied') < two_weeks_ago),
        'four_weeks_ago': sum(1 for app in applications if app.get('date_applied') and four_weeks_ago <= app.get('date_applied') < three_weeks_ago)
    }
    
    # Ensure all stats have at least a zero value
    for key in ['applied', 'in_progress', 'interviews', 'offers', 'rejected', 
                'last_week', 'two_weeks_ago', 'three_weeks_ago', 'four_weeks_ago']:
        if key not in stats or stats[key] is None:
            stats[key] = 0
    
    # Get upcoming deadlines (next 7 days)
    seven_days_later = today + timedelta(days=7)
    
    upcoming_deadlines = [
        app for app in applications 
        if app.get('deadline') and today <= app.get('deadline') <= seven_days_later
    ]
    
    # Sort deadlines by date (closest first)
    upcoming_deadlines.sort(key=lambda x: x.get('deadline'))
    
    # Get applications with interview status
    upcoming_interviews = [
        app for app in applications 
        if app.get('status') == 'Interview'
    ]
    
    return render_template(
        'dashboard.html', 
        stats=stats, 
        applications=applications,
        upcoming_deadlines=upcoming_deadlines,
        upcoming_interviews=upcoming_interviews
    )

@main.route('/application/new', methods=['GET', 'POST'])
@login_required
def add_application():
    if request.method == 'POST':
        # Process deadline if provided
        deadline = None
        if request.form.get('deadline'):
            try:
                deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d')
            except ValueError:
                pass
        
        application = {
            'user_id': str(current_user.id),
            'company': request.form.get('company'),
            'position': request.form.get('position'),
            'status': request.form.get('status'),
            'notes': request.form.get('notes'),
            'date_applied': datetime.now(),
            'url': request.form.get('url') if request.form.get('url') else None,
            'deadline': deadline,
            'company_logo': None  # You can add logo functionality later
        }
        
        mongo.db.applications.insert_one(application)
        flash('Application added successfully!', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('application_form.html')

@main.route('/application/edit/<application_id>', methods=['GET', 'POST'])
@login_required
def edit_application(application_id):
    # Get the application
    application = mongo.db.applications.find_one({
        '_id': ObjectId(application_id),
        'user_id': str(current_user.id)
    })
    
    if not application:
        flash('Application not found.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Process deadline if provided
        deadline = None
        if request.form.get('deadline'):
            try:
                deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d')
            except ValueError:
                pass
        
        # Update the application
        updates = {
            'company': request.form.get('company'),
            'position': request.form.get('position'),
            'status': request.form.get('status'),
            'notes': request.form.get('notes'),
            'url': request.form.get('url') if request.form.get('url') else None,
            'deadline': deadline
        }
        
        mongo.db.applications.update_one(
            {'_id': ObjectId(application_id)},
            {'$set': updates}
        )
        
        flash('Application updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    # Convert ObjectId to string for template
    application['_id'] = str(application['_id'])
    return render_template('application_form.html', application=application)

@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Handle profile update
        name = request.form.get('name')
        if name:
            mongo.db.users.update_one(
                {'_id': ObjectId(current_user.id)},
                {'$set': {'name': name}}
            )
            flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.settings'))
    
    return render_template('settings.html')

@main.route('/update_email_settings', methods=['POST'])
@login_required
def update_email_settings():
    auto_scan = 'auto_scan' in request.form
    require_approval = 'require_approval' in request.form
    scan_attachments = 'scan_attachments' in request.form
    
    settings = {
        'auto_scan': auto_scan,
        'require_approval': require_approval,
        'scan_attachments': scan_attachments,
        'last_scan': current_user.email_settings.get('last_scan') if hasattr(current_user, 'email_settings') and current_user.email_settings else None
    }
    
    # Update user settings
    mongo.db.users.update_one(
        {'_id': ObjectId(current_user.id)},
        {'$set': {'email_settings': settings}}
    )
    
    flash('Email settings updated successfully!', 'success')
    return redirect(url_for('main.settings'))

@main.route('/connect_gmail')
@login_required
def connect_gmail():
    # Check if Google API credentials are configured
    if not os.environ.get('GOOGLE_CLIENT_ID') or not os.environ.get('GOOGLE_CLIENT_SECRET'):
        flash('Google API credentials are not configured. Please contact the administrator.', 'error')
        return redirect(url_for('main.settings'))
    
    # Generate OAuth URL
    auth_url = EmailService.get_gmail_auth_url(current_user.id)
    return redirect(auth_url)

@main.route('/gmail_callback')
@login_required
def gmail_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('main.settings'))
    
    # Handle callback
    success, user = EmailService.handle_gmail_callback(code, state)
    
    if success:
        flash('Gmail connected successfully!', 'success')
    else:
        flash('Failed to connect Gmail. Please try again.', 'error')
    
    return redirect(url_for('main.settings'))

@main.route('/connect_outlook')
@login_required
def connect_outlook():
    flash('Outlook integration is coming soon!', 'info')
    return redirect(url_for('main.settings'))

@main.route('/connect_yahoo')
@login_required
def connect_yahoo():
    # Check if Yahoo API credentials are configured
    if not os.environ.get('YAHOO_CLIENT_ID') or not os.environ.get('YAHOO_CLIENT_SECRET'):
        flash('Yahoo API credentials are not configured. Please contact the administrator.', 'error')
        return redirect(url_for('main.settings'))
    
    # Generate OAuth URL
    auth_url = EmailService.get_yahoo_auth_url(current_user.id)
    return redirect(auth_url)

@main.route('/yahoo_callback')
@login_required
def yahoo_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('main.settings'))
    
    # Handle callback
    success, user = EmailService.handle_yahoo_callback(code, state)
    
    if success:
        flash('Yahoo Mail connected successfully!', 'success')
    else:
        flash('Failed to connect Yahoo Mail. Please try again.', 'error')
    
    return redirect(url_for('main.settings'))

@main.route('/disconnect_email', methods=['POST'])
@login_required
def disconnect_email():
    # Disconnect email
    current_user.disconnect_email()
    flash('Email disconnected successfully!', 'success')
    return redirect(url_for('main.settings'))

@main.route('/scan_emails')
@login_required
def scan_emails():
    if not current_user.email_connected:
        flash('Please connect your email first.', 'error')
        return redirect(url_for('main.settings'))
    
    # Scan emails
    success, message = EmailService.scan_emails(current_user)
    
    if success:
        flash(message, 'success')
        return redirect(url_for('main.email_suggestions'))
    else:
        flash(f'Failed to scan emails: {message}', 'error')
        return redirect(url_for('main.settings'))

@main.route('/email_suggestions')
@login_required
def email_suggestions():
    # Get suggestions for current user
    suggestions_doc = mongo.db.email_suggestions.find_one({
        'user_id': str(current_user.id),
        'processed': False
    })
    
    if not suggestions_doc:
        return render_template('email_suggestions.html', suggestions=None)
    
    # Process suggestions
    status_updates = []
    new_applications = []
    
    for suggestion in suggestions_doc['suggestions']:
        suggestion['id'] = str(suggestions_doc['_id'])
        if suggestion['type'] == 'update':
            status_updates.append(suggestion)
        elif suggestion['type'] == 'new':
            new_applications.append(suggestion)
    
    return render_template(
        'email_suggestions.html',
        suggestions=suggestions_doc,
        status_updates=status_updates,
        new_applications=new_applications
    )

@main.route('/accept_suggestion/<suggestion_id>', methods=['POST'])
@login_required
def accept_suggestion(suggestion_id):
    # Find suggestion
    suggestions_doc = mongo.db.email_suggestions.find_one({
        '_id': ObjectId(suggestion_id),
        'user_id': str(current_user.id)
    })
    
    if not suggestions_doc:
        flash('Suggestion not found.', 'error')
        return redirect(url_for('main.email_suggestions'))
    
    # Get suggestion index from form
    index = int(request.form.get('index', 0))
    
    if index >= len(suggestions_doc['suggestions']):
        flash('Invalid suggestion index.', 'error')
        return redirect(url_for('main.email_suggestions'))
    
    suggestion = suggestions_doc['suggestions'][index]
    
    # Process suggestion
    if suggestion['type'] == 'update':
        # Update application status
        mongo.db.applications.update_one(
            {'_id': ObjectId(suggestion['application_id'])},
            {'$set': {'status': suggestion['new_status']}}
        )
        flash(f"Updated status for {suggestion['company']} to {suggestion['new_status']}.", 'success')
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
        flash(f"Added new application for {suggestion['company']}.", 'success')
    
    # Mark suggestion as processed
    suggestions_doc['suggestions'].pop(index)
    
    if not suggestions_doc['suggestions']:
        # If no more suggestions, mark the whole document as processed
        mongo.db.email_suggestions.update_one(
            {'_id': ObjectId(suggestion_id)},
            {'$set': {'processed': True}}
        )
    else:
        # Otherwise, update the suggestions list
        mongo.db.email_suggestions.update_one(
            {'_id': ObjectId(suggestion_id)},
            {'$set': {'suggestions': suggestions_doc['suggestions']}}
        )
    
    return redirect(url_for('main.email_suggestions'))

@main.route('/reject_suggestion/<suggestion_id>', methods=['POST'])
@login_required
def reject_suggestion(suggestion_id):
    # Find suggestion
    suggestions_doc = mongo.db.email_suggestions.find_one({
        '_id': ObjectId(suggestion_id),
        'user_id': str(current_user.id)
    })
    
    if not suggestions_doc:
        flash('Suggestion not found.', 'error')
        return redirect(url_for('main.email_suggestions'))
    
    # Get suggestion index from form
    index = int(request.form.get('index', 0))
    
    if index >= len(suggestions_doc['suggestions']):
        flash('Invalid suggestion index.', 'error')
        return redirect(url_for('main.email_suggestions'))
    
    # Remove suggestion
    suggestion = suggestions_doc['suggestions'].pop(index)
    
    if not suggestions_doc['suggestions']:
        # If no more suggestions, mark the whole document as processed
        mongo.db.email_suggestions.update_one(
            {'_id': ObjectId(suggestion_id)},
            {'$set': {'processed': True}}
        )
    else:
        # Otherwise, update the suggestions list
        mongo.db.email_suggestions.update_one(
            {'_id': ObjectId(suggestion_id)},
            {'$set': {'suggestions': suggestions_doc['suggestions']}}
        )
    
    flash(f"Ignored suggestion for {suggestion['company']}.", 'success')
    return redirect(url_for('main.email_suggestions'))

@main.route('/test_db')
def test_db():
    try:
        # Test the database connection
        mongo.db.command('ping')
        
        # Get database information
        db_stats = mongo.db.command("dbStats")
        
        # Get collection stats
        users_count = mongo.db.users.count_documents({})
        apps_count = mongo.db.applications.count_documents({})
        
        # Get MongoDB connection info
        conn_info = mongo.cx.address if mongo.cx else "Not connected"
        
        return {
            'status': 'success',
            'connection': str(conn_info),
            'database_name': mongo.db.name,
            'collections': {
                'users': users_count,
                'applications': apps_count
            },
            'database_stats': {
                'collections': db_stats.get('collections', 0),
                'objects': db_stats.get('objects', 0),
                'avgObjSize': db_stats.get('avgObjSize', 0),
                'dataSize': db_stats.get('dataSize', 0),
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

@main.route('/application/delete/<application_id>', methods=['POST'])
@login_required
def delete_application(application_id):
    # Verify the application belongs to the current user
    application = mongo.db.applications.find_one({
        '_id': ObjectId(application_id),
        'user_id': str(current_user.id)
    })
    
    if not application:
        flash('Application not found or you do not have permission to delete it.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Delete the application
    result = mongo.db.applications.delete_one({
        '_id': ObjectId(application_id),
        'user_id': str(current_user.id)
    })
    
    if result.deleted_count > 0:
        flash('Application deleted successfully!', 'success')
    else:
        flash('Failed to delete application.', 'error')
    
    return redirect(url_for('main.dashboard')) 