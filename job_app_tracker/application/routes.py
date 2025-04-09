from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from job_app_tracker.models.application import Application
from job_app_tracker.utils.company_logo import get_company_logo_url
from datetime import datetime

application = Blueprint('application', __name__)

@application.route('/application/create', methods=['POST'])
@login_required
def create_application():
    data = request.get_json()
    
    # Get company logo if URL is provided
    url = data.get('url')
    company_logo = get_company_logo_url(url) if url else None
    
    application = Application.create_application(
        user_id=current_user.id,
        company=data.get('company'),
        position=data.get('position'),
        status=data.get('status', 'Applied'),
        notes=data.get('notes', ''),
        date_applied=data.get('date_applied', datetime.utcnow()),
        url=url,
        deadline=data.get('deadline'),
        company_logo=company_logo
    )
    
    return jsonify(application), 201

@application.route('/application/update/<application_id>', methods=['PUT'])
@login_required
def update_application(application_id):
    data = request.get_json()
    
    # Get company logo if URL is provided and changed
    url = data.get('url')
    if url:
        company_logo = get_company_logo_url(url)
        data['company_logo'] = company_logo
    
    application = Application.update_application(
        application_id=application_id,
        user_id=current_user.id,
        **data
    )
    
    if application:
        return jsonify(application)
    return jsonify({'error': 'Application not found'}), 404 