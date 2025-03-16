from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from job_app_tracker.config.mongodb import mongo
from datetime import datetime, timedelta
from bson import ObjectId
from job_app_tracker.services.email_service import EmailService
import os
from job_app_tracker.models.application import Application
from werkzeug.utils import secure_filename
from flask import current_app

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main.route('/faq')
def faq():
    return render_template('faq.html')

@main.route('/pricing')
def pricing():
    return render_template('pricing.html')

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

@main.route('/upgrade', methods=['POST'])
@login_required
def upgrade_subscription():
    # This is a placeholder for the actual payment processing
    # In a real implementation, you would integrate with a payment processor like Stripe
    
    # For now, we'll just simulate a successful upgrade
    from datetime import datetime, timedelta
    
    # Set subscription to premium for 30 days
    current_user.update_subscription(
        is_premium=True,
        plan='premium',
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30),
        payment_id='simulated_payment_' + str(datetime.now().timestamp())
    )
    
    flash('Congratulations! Your account has been upgraded to Premium for 30 days.', 'success')
    return redirect(url_for('main.dashboard'))

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

@main.route('/clear_email_cache', methods=['POST'])
@login_required
def clear_email_cache():
    """Clear the email analysis cache for the current user"""
    # Check if user is premium
    if not current_user.is_premium:
        flash('Cache management is a premium feature.', 'error')
        return redirect(url_for('main.settings'))
    
    # Clear cache for this user
    from job_app_tracker.services.email_service import EmailService
    deleted_count = EmailService.clear_analysis_cache(user_id=current_user.id)
    
    if deleted_count > 0:
        flash(f'Successfully cleared {deleted_count} cached email analyses.', 'success')
    else:
        flash('No cached analyses found to clear.', 'info')
    
    return redirect(url_for('main.settings'))

@main.route('/scan_emails')
@login_required
def scan_emails():
    if not current_user.email_connected:
        flash('Please connect your email first.', 'error')
        return redirect(url_for('main.settings'))
    
    # Scan emails
    success, message, redirect_endpoint = EmailService.scan_emails(current_user)
    
    if success:
        flash(message, 'success')
    else:
        flash(f'Failed to scan emails: {message}', 'error')
    
    # Use the redirect endpoint directly
    return redirect(url_for(redirect_endpoint))

@main.route('/email_suggestions')
@login_required
def email_suggestions():
    """Show email suggestions for job applications"""
    user = current_user
    
    # Get page number from query parameters, default to 1
    page = request.args.get('page', 1, type=int)
    items_per_page = 10  # Number of suggestions per page
    
    # Get suggestions from database
    suggestions = mongo.db.email_suggestions.find_one({
        'user_id': str(user.id),
        'processed': False
    })
    
    if not suggestions:
        return render_template(
            'email_suggestions.html',
            suggestions=None,
            status_updates=None,
            new_applications=None,
            current_page=1,
            total_pages=1,
            has_next=False,
            has_prev=False
        )
    
    # Process suggestions
    status_updates = []
    new_applications = []
    
    for i, suggestion in enumerate(suggestions['suggestions']):
        suggestion['index'] = i
        if suggestion['type'] == 'update':
            status_updates.append(suggestion)
        elif suggestion['type'] == 'new':
            new_applications.append(suggestion)
    
    # Implement pagination
    total_status_updates = len(status_updates)
    total_new_applications = len(new_applications)
    
    # Determine which section to paginate based on what's available
    if status_updates and page <= (total_status_updates + items_per_page - 1) // items_per_page:
        # Paginate status updates
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_status_updates)
        paginated_status_updates = status_updates[start_idx:end_idx]
        paginated_new_applications = []
        section = "updates"
        total_items = total_status_updates
    else:
        # Paginate new applications
        # Adjust page number to account for status update pages
        adjusted_page = page - ((total_status_updates + items_per_page - 1) // items_per_page)
        start_idx = (adjusted_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_new_applications)
        paginated_status_updates = []
        paginated_new_applications = new_applications[start_idx:end_idx]
        section = "new"
        total_items = total_new_applications
    
    # Calculate total pages across both sections
    total_update_pages = (total_status_updates + items_per_page - 1) // items_per_page
    total_new_pages = (total_new_applications + items_per_page - 1) // items_per_page
    total_pages = total_update_pages + total_new_pages
    
    # Check if there are next/previous pages
    has_next = page < total_pages
    has_prev = page > 1
    
    return render_template(
        'email_suggestions.html',
        suggestions=suggestions,
        status_updates=paginated_status_updates,
        new_applications=paginated_new_applications,
        current_page=page,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        section=section,
        items_per_page=items_per_page
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
    
    # Get selected suggestions from form
    selected = request.form.getlist('accept')
    
    if not selected:
        flash('No suggestions selected.', 'warning')
        return redirect(url_for('main.email_suggestions'))
    
    processed_count = 0
    
    for selection in selected:
        # Handle new applications (format: "new_X")
        if selection.startswith('new_'):
            try:
                index = int(selection.split('_')[1])
                if index < len(suggestions_doc['suggestions']):
                    suggestion = suggestions_doc['suggestions'][index]
                    if suggestion['type'] == 'new':
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
                        processed_count += 1
                        # Mark as processed by setting to None (we'll filter these out later)
                        suggestions_doc['suggestions'][index] = None
            except (ValueError, IndexError):
                continue
        else:
            # Handle status updates (application_id directly)
            try:
                app_id = selection
                # Find the suggestion with this application_id
                for i, suggestion in enumerate(suggestions_doc['suggestions']):
                    if suggestion and suggestion['type'] == 'update' and suggestion.get('application_id') == app_id:
                        # Update application status
                        mongo.db.applications.update_one(
                            {'_id': ObjectId(suggestion['application_id'])},
                            {'$set': {'status': suggestion['new_status']}}
                        )
                        processed_count += 1
                        # Mark as processed by setting to None
                        suggestions_doc['suggestions'][i] = None
                        break
            except Exception as e:
                current_app.logger.error(f"Error processing suggestion: {str(e)}")
                continue
    
    # Remove processed suggestions (None values)
    suggestions_doc['suggestions'] = [s for s in suggestions_doc['suggestions'] if s is not None]
    
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
    
    if processed_count > 0:
        flash(f"Successfully processed {processed_count} suggestion(s).", 'success')
    else:
        flash("No suggestions were processed.", 'warning')
    
    return redirect(url_for('main.email_suggestions'))

@main.route('/accept_all_suggestions/<suggestion_id>', methods=['POST'])
@login_required
def accept_all_suggestions(suggestion_id):
    """Process all suggestions at once"""
    # Find suggestion document
    suggestions_doc = mongo.db.email_suggestions.find_one({
        '_id': ObjectId(suggestion_id),
        'user_id': str(current_user.id)
    })
    
    if not suggestions_doc:
        flash('Suggestions not found.', 'error')
        return redirect(url_for('main.email_suggestions'))
    
    # Check if the user wants to process all suggestions
    if not request.form.get('select_all'):
        flash('No suggestions selected.', 'warning')
        return redirect(url_for('main.email_suggestions'))
    
    processed_count = 0
    new_applications = []
    status_updates = []
    
    # Process all suggestions
    for i, suggestion in enumerate(suggestions_doc['suggestions']):
        if suggestion['type'] == 'new':
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
            
            # Add job URL if available
            if suggestion.get('job_url'):
                new_app['url'] = suggestion['job_url']
                
            # Add application platform if available
            if suggestion.get('application_platform'):
                if new_app.get('notes'):
                    new_app['notes'] += f" | Applied via {suggestion['application_platform']}"
                else:
                    new_app['notes'] = f"Applied via {suggestion['application_platform']}"
                
            new_applications.append(new_app)
            processed_count += 1
        elif suggestion['type'] == 'update':
            # Add to status updates list
            status_updates.append({
                'application_id': suggestion['application_id'],
                'new_status': suggestion['new_status']
            })
            processed_count += 1
    
    # Bulk insert new applications
    if new_applications:
        mongo.db.applications.insert_many(new_applications)
    
    # Bulk update status updates
    for update in status_updates:
        try:
            mongo.db.applications.update_one(
                {'_id': ObjectId(update['application_id'])},
                {'$set': {'status': update['new_status']}}
            )
        except Exception as e:
            current_app.logger.error(f"Error updating application status: {str(e)}")
    
    # Mark all suggestions as processed
    mongo.db.email_suggestions.update_one(
        {'_id': ObjectId(suggestion_id)},
        {'$set': {'processed': True}}
    )
    
    flash(f"Successfully processed all {processed_count} suggestions!", 'success')
    return redirect(url_for('main.dashboard'))

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

@main.route('/cache_stats')
@login_required
def cache_stats():
    """Get statistics about the email analysis cache"""
    # Check if user is premium
    if not current_user.is_premium:
        flash('Cache management is a premium feature.', 'error')
        return redirect(url_for('main.settings'))
    
    try:
        # Get overall cache stats
        total_cache_entries = mongo.db.analysis_cache.count_documents({})
        
        # Get user's cache stats
        user_cache_entries = mongo.db.analysis_cache.count_documents({"user_id": str(current_user.id)})
        
        # Get cache size by status
        job_related_entries = mongo.db.analysis_cache.count_documents({"is_job_related": True})
        non_job_related_entries = mongo.db.analysis_cache.count_documents({"is_job_related": False})
        
        # Get cache age statistics
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_entries = mongo.db.analysis_cache.count_documents({"created_at": {"$gte": one_day_ago}})
        week_old_entries = mongo.db.analysis_cache.count_documents({
            "created_at": {"$lt": one_day_ago, "$gte": one_week_ago}
        })
        older_entries = mongo.db.analysis_cache.count_documents({"created_at": {"$lt": one_week_ago}})
        
        # Get most common companies in cache
        pipeline = [
            {"$match": {"company": {"$ne": "Unknown Company"}}},
            {"$group": {"_id": "$company", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        top_companies = list(mongo.db.analysis_cache.aggregate(pipeline))
        
        return render_template(
            'cache_stats.html',
            total_cache_entries=total_cache_entries,
            user_cache_entries=user_cache_entries,
            job_related_entries=job_related_entries,
            non_job_related_entries=non_job_related_entries,
            recent_entries=recent_entries,
            week_old_entries=week_old_entries,
            older_entries=older_entries,
            top_companies=top_companies
        )
    except Exception as e:
        flash(f'Error retrieving cache statistics: {str(e)}', 'error')
        return redirect(url_for('main.settings'))

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

@main.route('/application/notes/<application_id>', methods=['GET', 'POST'])
@login_required
def application_notes(application_id):
    # Get the application using our new model
    application = Application.get_by_id(application_id, current_user.id)
    
    if not application:
        flash('Application not found.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        content = request.form.get('note_content')
        if content:
            application.add_note(content)
            flash('Note added successfully!', 'success')
        
        return redirect(url_for('main.application_notes', application_id=application_id))
    
    return render_template('application_notes.html', application=application)

@main.route('/application/note/edit/<application_id>/<note_id>', methods=['POST'])
@login_required
def edit_note(application_id, note_id):
    application = Application.get_by_id(application_id, current_user.id)
    
    if not application:
        return jsonify({'success': False, 'message': 'Application not found'}), 404
    
    content = request.form.get('content')
    if not content:
        return jsonify({'success': False, 'message': 'Note content is required'}), 400
    
    success = application.update_note(note_id, content)
    
    if success:
        return jsonify({'success': True, 'message': 'Note updated successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to update note'}), 500

@main.route('/application/note/delete/<application_id>/<note_id>', methods=['POST'])
@login_required
def delete_note(application_id, note_id):
    application = Application.get_by_id(application_id, current_user.id)
    
    if not application:
        return jsonify({'success': False, 'message': 'Application not found'}), 404
    
    success = application.delete_note(note_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Note deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete note'}), 500

@main.route('/application/documents/<application_id>', methods=['GET', 'POST'])
@login_required
def application_documents(application_id):
    application = Application.get_by_id(application_id, current_user.id)
    
    if not application:
        flash('Application not found.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        if 'document' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['document']
        
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        if file:
            # Generate a secure filename
            filename = secure_filename(file.filename)
            
            # Create a unique filename with timestamp
            unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            
            # Create user directory if it doesn't exist
            user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            
            # Save the file
            file_path = os.path.join(user_dir, unique_filename)
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Add document to application
            application.add_document(
                name=filename,
                file_path=file_path,
                file_type=file.content_type,
                size=file_size
            )
            
            flash('Document uploaded successfully!', 'success')
        
        return redirect(url_for('main.application_documents', application_id=application_id))
    
    return render_template('application_documents.html', application=application)

@main.route('/application/document/delete/<application_id>/<document_id>', methods=['POST'])
@login_required
def delete_document(application_id, document_id):
    application = Application.get_by_id(application_id, current_user.id)
    
    if not application:
        return jsonify({'success': False, 'message': 'Application not found'}), 404
    
    # Find the document to get its file path
    document = None
    for doc in application.documents:
        if doc['id'] == document_id:
            document = doc
            break
    
    if not document:
        return jsonify({'success': False, 'message': 'Document not found'}), 404
    
    # Delete the file if it exists
    if 'file_path' in document and os.path.exists(document['file_path']):
        try:
            os.remove(document['file_path'])
        except:
            # Log the error but continue
            current_app.logger.error(f"Failed to delete file: {document['file_path']}")
    
    # Remove document from application
    success = application.delete_document(document_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Document deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete document'}), 500

@main.route('/application/interviews/<application_id>', methods=['GET', 'POST'])
@login_required
def application_interviews(application_id):
    # Get the application using our new model
    application = Application.get_by_id(application_id, current_user.id)
    if not application:
        flash('Application not found.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            interview_date_str = request.form.get('interview_date')
            interview_type = request.form.get('interview_type')
            interview_notes = request.form.get('interview_notes', '')
            
            # Validate required fields
            if not interview_date_str or not interview_type:
                flash('Interview date and type are required.', 'error')
                return redirect(url_for('main.application_interviews', application_id=application_id))
            
            # Parse date
            try:
                interview_date = datetime.fromisoformat(interview_date_str)
            except ValueError:
                flash('Invalid date format.', 'error')
                return redirect(url_for('main.application_interviews', application_id=application_id))
            
            # Add interview
            application.add_interview(interview_date, interview_type, interview_notes)
            
            # Update application status to Interview if it's currently Applied
            if application.status == 'Applied':
                application.update({'status': 'Interview'})
            
            flash('Interview added successfully.', 'success')
        except Exception as e:
            flash(f'Error adding interview: {str(e)}', 'error')
        
        return redirect(url_for('main.application_interviews', application_id=application_id))
    
    # Pass current datetime for template calculations
    now = datetime.now()
    
    return render_template('application_interviews.html', application=application, now=now)

@main.route('/application/interview/delete/<application_id>/<interview_id>', methods=['POST'])
@login_required
def delete_interview(application_id, interview_id):
    # Get the application
    application = Application.get_by_id(application_id, current_user.id)
    if not application:
        return jsonify({'success': False, 'message': 'Application not found.'})
    
    # Check if the interview exists
    interview_exists = False
    for interview in application.interviews:
        if interview.get('id') == interview_id:
            interview_exists = True
            break
    
    if not interview_exists:
        return jsonify({'success': False, 'message': 'Interview not found.'})
    
    # Delete the interview
    try:
        # Update MongoDB
        mongo.db.applications.update_one(
            {'_id': ObjectId(application_id)},
            {
                '$pull': {'interviews': {'id': interview_id}},
                '$set': {'updated_at': datetime.now()}
            }
        )
        
        # Update local object
        application.interviews = [i for i in application.interviews if i.get('id') != interview_id]
        application.updated_at = datetime.now()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@main.route('/clear_all_user_data')
@login_required
def clear_all_user_data():
    # Clear all user data
    deleted_count = EmailService.clear_all_user_data(current_user)
    
    flash(f'Cleared {deleted_count["suggestions"]} suggestions and {deleted_count["applications"]} applications.', 'success')
    
    # Redirect to email suggestions page
    return redirect(url_for('main.email_suggestions')) 