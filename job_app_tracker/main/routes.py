from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from job_app_tracker.config.mongodb import mongo
from datetime import datetime, timedelta
from bson import ObjectId

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

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

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

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