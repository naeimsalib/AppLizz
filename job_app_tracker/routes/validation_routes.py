from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import json
from pathlib import Path

from job_app_tracker.models.user import User
from job_app_tracker.config.logging import logger

validation_bp = Blueprint('validation', __name__)

@validation_bp.route('/email-validation', methods=['GET'])
@login_required
def email_validation():
    """Email validation dashboard"""
    # Get validation stats for the current user
    validation_stats = current_user.get_validation_stats()
    
    # Get list of validation logs if they exist
    log_dir = Path('job_app_tracker/logs/validation')
    validation_logs = []
    
    if log_dir.exists():
        # Find validation logs for this user
        validation_logs = list(log_dir.glob(f"validation_{current_user.id}_*.csv"))
        validation_logs = [str(log.name) for log in validation_logs]
        
    # Get list of summary files
    summary_dir = Path('job_app_tracker/logs/validation')
    summary_files = []
    
    if summary_dir.exists():
        # Find summary files for this user
        summary_files = list(summary_dir.glob(f"summary_{current_user.id}_*.json"))
        summary_files = [
            {
                'name': log.name,
                'date': log.stat().st_mtime,
                'path': str(log)
            }
            for log in summary_files
        ]
        
        # Sort by date (newest first)
        summary_files.sort(key=lambda x: x['date'], reverse=True)
        
    return render_template(
        'validation/dashboard.html',
        validation_stats=validation_stats,
        validation_logs=validation_logs,
        summary_files=summary_files
    )

@validation_bp.route('/email-validation/run', methods=['POST'])
@login_required
def run_validation():
    """Run email validation for the current user"""
    if not current_user.email_connected:
        flash('You need to connect an email account first.', 'warning')
        return redirect(url_for('settings'))
        
    # Get parameters from form
    batch_size = int(request.form.get('batch_size', 100))
    max_emails = int(request.form.get('max_emails', 1000))
    suggest_improvements = request.form.get('suggest_improvements') == 'on'
    apply_improvements = request.form.get('apply_improvements') == 'on'
    
    # Run validation
    result = current_user.run_email_validation(
        batch_size=batch_size,
        max_emails=max_emails,
        suggest_improvements=suggest_improvements,
        apply_improvements=apply_improvements
    )
    
    if result['success']:
        flash('Email validation completed successfully.', 'success')
    else:
        flash(f"Error running validation: {result.get('error')}", 'danger')
        
    return redirect(url_for('validation.email_validation'))

@validation_bp.route('/email-validation/logs/<log_file>', methods=['GET'])
@login_required
def view_log(log_file):
    """View validation log file"""
    log_path = Path('job_app_tracker/logs/validation') / log_file
    
    if not log_path.exists():
        flash('Log file not found.', 'danger')
        return redirect(url_for('validation.email_validation'))
        
    # Check if this log belongs to the current user
    if not log_file.startswith(f"validation_{current_user.id}_"):
        flash('You do not have permission to view this log.', 'danger')
        return redirect(url_for('validation.email_validation'))
        
    # Read log file
    with open(log_path, 'r') as f:
        log_content = f.read()
        
    return render_template(
        'validation/view_log.html',
        log_file=log_file,
        log_content=log_content
    )

@validation_bp.route('/email-validation/summary/<summary_file>', methods=['GET'])
@login_required
def view_summary(summary_file):
    """View validation summary file"""
    summary_path = Path('job_app_tracker/logs/validation') / summary_file
    
    if not summary_path.exists():
        flash('Summary file not found.', 'danger')
        return redirect(url_for('validation.email_validation'))
        
    # Check if this summary belongs to the current user
    if not summary_file.startswith(f"summary_{current_user.id}_"):
        flash('You do not have permission to view this summary.', 'danger')
        return redirect(url_for('validation.email_validation'))
        
    # Read summary file
    with open(summary_path, 'r') as f:
        summary_data = json.load(f)
        
    return render_template(
        'validation/view_summary.html',
        summary_file=summary_file,
        summary_data=summary_data
    )

@validation_bp.route('/api/validation-stats', methods=['GET'])
@login_required
def api_validation_stats():
    """API endpoint for validation stats"""
    validation_stats = current_user.get_validation_stats()
    
    if not validation_stats:
        return jsonify({
            'success': False,
            'error': 'No validation stats available'
        })
        
    return jsonify({
        'success': True,
        'stats': validation_stats
    })
    
@validation_bp.route('/api/run-validation', methods=['POST'])
@login_required
def api_run_validation():
    """API endpoint for running validation"""
    if not current_user.email_connected:
        return jsonify({
            'success': False,
            'error': 'No email connected for this user'
        })
        
    # Get parameters from JSON data
    data = request.get_json()
    
    batch_size = data.get('batch_size', 100)
    max_emails = data.get('max_emails', 1000)
    suggest_improvements = data.get('suggest_improvements', True)
    apply_improvements = data.get('apply_improvements', False)
    
    # Run validation
    result = current_user.run_email_validation(
        batch_size=batch_size,
        max_emails=max_emails,
        suggest_improvements=suggest_improvements,
        apply_improvements=apply_improvements
    )
    
    return jsonify(result) 