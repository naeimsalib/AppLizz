from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from job_app_tracker.config.mongodb import mongo
from datetime import datetime, timedelta
from bson import ObjectId
import os
from job_app_tracker.models.application import Application
from werkzeug.utils import secure_filename
from flask import current_app
import json

main = Blueprint('main', __name__)

# Define job application statuses
JOB_APPLICATION_STATUSES = ['Applied', 'In Progress', 'Interview', 'Offer', 'Rejected', 'Withdrawn']

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
    """Route for the dashboard page."""
    # Get all job applications for the current user
    job_applications = Application.get_all_for_user(current_user.id)

    # Get counts for each status
    status_counts = {}
    for status in JOB_APPLICATION_STATUSES:
        status_counts[status] = sum(1 for app in job_applications if app.status == status)

    # Also add "In Progress" status which might not be in JOB_APPLICATION_STATUSES
    if 'In Progress' not in status_counts:
        status_counts['In Progress'] = sum(1 for app in job_applications if app.status == 'In Progress')

    # Calculate statistics
    total_applications = len(job_applications)
    active_applications = sum(status_counts.get(status, 0) for status in ['Applied', 'In Progress', 'Interview'])
    rejected_applications = status_counts.get('Rejected', 0)
    
    # Get recent applications (limited to 5)
    recent_applications = sorted(
        job_applications, 
        key=lambda x: x.created_at if x.created_at else datetime.min, 
        reverse=True
    )[:5]

    # Compute application timeline (last 30 days)
    today = datetime.now().date()
    timeline_data = {}
    
    # Initialize the timeline with zeros for the last 30 days
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        timeline_data[date.strftime('%Y-%m-%d')] = 0
    
    # Count applications for each day
    for app in job_applications:
        if app.created_at:
            app_date = app.created_at.date()
            date_diff = (today - app_date).days
            
            if 0 <= date_diff <= 30:
                date_str = app_date.strftime('%Y-%m-%d')
                timeline_data[date_str] = timeline_data.get(date_str, 0) + 1
    
    # Prepare timeline data for charts
    timeline_labels = list(timeline_data.keys())
    timeline_values = list(timeline_data.values())
    
    return render_template(
        'dashboard.html',
        job_applications=job_applications,
        recent_applications=recent_applications,
        total_applications=total_applications,
        active_applications=active_applications,
        rejected_applications=rejected_applications,
        status_counts=status_counts,
        timeline_labels=timeline_labels,
        timeline_values=timeline_values,
        page='dashboard'
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
    """User settings page"""
    # Display basic settings page without email functionality
    
    # Get user data
    from flask_pymongo import PyMongo
    mongo = PyMongo(current_app)
    
    user_data = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
    
    return render_template(
        'settings.html', 
        user=current_user,
        user_data=user_data
    )

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