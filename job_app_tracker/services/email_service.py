import logging
from datetime import datetime, timedelta
import threading
import time
from flask import flash, current_app
import random
from bson.objectid import ObjectId

logger = logging.getLogger('email_service')

class EmailService:
    """Email Service class that provides email scanning functionality."""
    
    @staticmethod
    def _analyze_email_content(subject, body, from_email):
        """Simplified email analysis that returns empty result."""
        return {
            'is_job_related': False,
            'company': 'Unknown Company',
            'position': 'Unknown Position',
            'status': 'Applied',
            'confidence': 0.5,
            'validation_checks': []
        }
    
    @staticmethod
    def generate_sample_job_suggestions(user, count=5):
        """
        Generate sample job application suggestions for testing
        
        Args:
            user: User object
            count: Number of suggestions to generate
            
        Returns:
            dict: Result with count of suggestions created
        """
        try:
            from flask_pymongo import PyMongo
            
            # Get MongoDB connection from app context
            mongo = PyMongo(current_app)
            user_id = str(user.id)
            
            # Sample companies and positions
            companies = [
                "Google", "Amazon", "Microsoft", "Apple", "Meta", 
                "Netflix", "Salesforce", "Adobe", "IBM", "Oracle",
                "Twitter", "Slack", "Zoom", "Dropbox", "Airbnb",
                "Uber", "Lyft", "DoorDash", "Instacart", "Robinhood"
            ]
            
            positions = [
                "Software Engineer", "Frontend Developer", "Backend Developer",
                "Full Stack Engineer", "Data Scientist", "Machine Learning Engineer",
                "DevOps Engineer", "Site Reliability Engineer", "Product Manager",
                "UX Designer", "UI Developer", "QA Engineer", "Technical Writer",
                "Engineering Manager", "Technical Product Manager", "Data Analyst",
                "Mobile Developer", "iOS Developer", "Android Developer", "Cloud Engineer"
            ]
            
            job_statuses = ["Applied", "Interview", "Offer", "Rejected"]
            
            # Generate email suggestions
            suggestions = []
            for i in range(count):
                company = f"[SAMPLE] {random.choice(companies)}"
                position = random.choice(positions)
                status = random.choice(job_statuses)
                date = datetime.now() - timedelta(days=random.randint(1, 30))
                
                # Create a unique email subject based on the application type
                if status == "Applied":
                    subject = f"[SAMPLE] Thank you for applying to {position} at {company}"
                    from_email = f"sample-careers@{company.lower().replace(' ', '').replace('[sample]', '').strip()}.com"
                elif status == "Interview":
                    subject = f"[SAMPLE] Interview invitation for {position} role at {company}"
                    from_email = f"sample-recruiting@{company.lower().replace(' ', '').replace('[sample]', '').strip()}.com"
                elif status == "Offer":
                    subject = f"[SAMPLE] Job Offer: {position} at {company}"
                    from_email = f"sample-hr@{company.lower().replace(' ', '').replace('[sample]', '').strip()}.com"
                else:  # Rejected
                    subject = f"[SAMPLE] Update on your application for {position} at {company}"
                    from_email = f"sample-no-reply@{company.lower().replace(' ', '').replace('[sample]', '').strip()}.com"
                
                # Generate a suggestion based on status
                suggestion = {
                    "type": "new",
                    "email_id": f"sample_{i}_{random.randint(1000, 9999)}",
                    "email_subject": subject,
                    "email_from": from_email,
                    "date": date,
                    "company": company,
                    "position": position,
                    "status": status,
                    "confidence": random.uniform(0.7, 0.95)
                }
                
                suggestions.append(suggestion)
            
            # Check if user already has suggestions
            existing = mongo.db.email_suggestions.find_one({
                'user_id': user_id,
                'processed': False
            })
            
            if existing:
                # Update existing suggestions
                updated_suggestions = existing['suggestions'] + suggestions
                mongo.db.email_suggestions.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'suggestions': updated_suggestions}}
                )
                result = {
                    'success': True,
                    'count': len(suggestions),
                    'total': len(updated_suggestions)
                }
            else:
                # Create new suggestions document
                suggestion_doc = {
                    'user_id': user_id,
                    'processed': False,
                    'created_at': datetime.now(),
                    'suggestions': suggestions
                }
                mongo.db.email_suggestions.insert_one(suggestion_doc)
                result = {
                    'success': True,
                    'count': len(suggestions),
                    'total': len(suggestions)
                }
            
            logger.info(f"Generated {len(suggestions)} sample job suggestions for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating sample suggestions: {str(e)}")
            return {
                'success': False,
                'count': 0,
                'total': 0,
                'error': str(e)
            }
    
    @staticmethod
    def scan_emails(user):
        """Scan emails for job-related content."""
        # This functionality is disabled in the free version
        logger.info(f"Email scanning disabled - returning explanation to user {user.id}")
        
        # Create a result class that works with both routes
        class ScanResult:
            def __init__(self, success, message, redirect_endpoint, processed_count=0, total_count=0, job_applications=None):
                self.success = success
                self.message = message
                self.redirect_endpoint = redirect_endpoint
                self.processed_count = processed_count
                self.total_count = total_count
                self.job_applications = job_applications or []
            
            def __getitem__(self, key):
                if isinstance(key, int):
                    if key == 0: return self.success
                    elif key == 1: return self.message
                    elif key == 2: return self.redirect_endpoint
                    else: raise IndexError("Index out of range")
                elif isinstance(key, str):
                    if key == 'success': return self.success
                    elif key == 'message': return self.message
                    elif key == 'processed_count': return self.processed_count
                    elif key == 'total_count': return self.total_count
                    elif key == 'job_applications': return self.job_applications
                    elif key == 'error': return None
                    else: return None
            
            def get(self, key, default=None):
                try:
                    result = self[key]
                    return result if result is not None else default
                except (IndexError, KeyError):
                    return default
                    
            def update(self, data):
                # No-op method to avoid errors
                pass
        
        # Return a message explaining the feature is coming soon
        return ScanResult(
            False, 
            "Email scanning is coming soon! This feature will be available in an upcoming update.", 
            "main.dashboard"
        )
        
        # ORIGINAL CODE COMMENTED OUT
        """
        # Check if user has connected email
        if not hasattr(user, 'email_provider') or not user.email_provider:
            logger.warning(f"User {user.id} has no connected email provider")
            return ScanResult(False, "No email provider connected", "main.settings")
        
        # Use appropriate service based on email provider
        email_provider = user.email_provider.lower()
        
        if email_provider in ['yahoo', 'yahoo_imap']:
            try:
                from job_app_tracker.services.yahoo_mail_service import YahooMailService
                logger.info(f"Using YahooMailService for user {user.id}")
                
                # Set user's last scan date to 15 days ago if not set
                if not hasattr(user, 'email_settings') or not user.email_settings or 'last_scan' not in user.email_settings:
                    from flask_pymongo import PyMongo
                    
                    # Get MongoDB connection from app context
                    mongo = PyMongo(current_app)
                    
                    # Set last scan date to 15 days ago
                    fifteen_days_ago = datetime.now() - timedelta(days=15)
                    mongo.db.users.update_one(
                        {'_id': ObjectId(user.id)},
                        {'$set': {'email_settings.last_scan': fifteen_days_ago}}
                    )
                    
                    logger.info(f"Updated user {user.id} last scan date to 15 days ago")
                
                # Perform Yahoo Mail scanning
                success, message, redirect_endpoint = YahooMailService.scan_emails(user, limit=100)
                
                # Get the number of suggestions created during the scan
                from flask_pymongo import PyMongo
                mongo = PyMongo(current_app)
                user_id = str(user.id)
                
                # Count unprocessed suggestions from scan
                suggestion_doc = mongo.db.email_suggestions.find_one({
                    'user_id': user_id,
                    'processed': False
                })
                
                suggestions_count = len(suggestion_doc.get('suggestions', [])) if suggestion_doc else 0
                logger.info(f"Scanning found {suggestions_count} job applications")
                
                return ScanResult(
                    success, 
                    message, 
                    redirect_endpoint,
                    processed_count=suggestions_count,
                    total_count=suggestions_count
                )
                
            except ImportError as e:
                logger.error(f"YahooMailService not available: {str(e)}")
                return ScanResult(
                    False, 
                    f"Yahoo Mail service not available: {str(e)}", 
                    "main.dashboard"
                )
            except Exception as e:
                logger.error(f"Error during email scanning: {str(e)}")
                return ScanResult(
                    False, 
                    f"Error scanning emails: {str(e)}", 
                    "main.dashboard"
                )
        else:
            logger.warning(f"Email provider '{user.email_provider}' not supported")
            return ScanResult(
                False, 
                f"Email provider '{user.email_provider}' not supported", 
                "main.settings"
            )
        """
    
    @staticmethod
    def get_gmail_auth_url(user_id):
        """Get Gmail authentication URL."""
        # Disabled in the free version
        logger.info(f"Gmail auth URL requested but feature is disabled for user {user_id}")
        return "#feature-disabled"
    
    @staticmethod
    def handle_gmail_callback(code, state):
        """Handle Gmail authentication callback."""
        # Disabled in the free version
        logger.info("Gmail callback handling disabled")
        return False, "This feature is coming soon in an upcoming update."
    
    @staticmethod
    def connect_yahoo_imap(user_id, yahoo_email, app_password):
        """Connect to Yahoo IMAP."""
        # Disabled in the free version
        logger.info(f"Yahoo IMAP connection requested but feature is disabled for user {user_id}")
        return False, "Email connection is coming soon in an upcoming update."
    
    @staticmethod
    def clear_all_user_data(user):
        """Clear all user data."""
        try:
            from flask_pymongo import PyMongo
            
            # Get MongoDB connection from app context
            mongo = PyMongo(current_app)
            user_id = str(user.id)
            
            # Clear email suggestions
            suggestions_result = mongo.db.email_suggestions.delete_many({'user_id': user_id})
            
            # Clear applications
            applications_result = mongo.db.applications.delete_many({'user_id': user_id})
            
            # Clear analysis cache
            cache_result = mongo.db.analysis_cache.delete_many({'user_id': user_id})
            
            # Reset last scan time
            user_update_result = mongo.db.users.update_one(
                {'_id': ObjectId(user.id)},
                {'$unset': {'email_settings.last_scan': ''}}
            )
            
            logger.info(f"Cleared data for user {user_id}: {suggestions_result.deleted_count} suggestions, {applications_result.deleted_count} applications")
            
            return {
                'suggestions': suggestions_result.deleted_count,
                'applications': applications_result.deleted_count,
                'cache': cache_result.deleted_count
            }
        except Exception as e:
            logger.error(f"Error clearing user data: {str(e)}")
            return {
                'suggestions': 0,
                'applications': 0,
                'cache': 0
            }
    
    @staticmethod
    def _get_cached_email(email_id, user_id):
        """Get cached email analysis data."""
        return None
    
    @staticmethod
    def _cache_email(email_id, user_id, analysis_data):
        """Cache email analysis data."""
        pass
    
    @staticmethod
    def _clear_cache():
        """Clear the email analysis cache."""
        pass
    
    @staticmethod
    def _cleanup_expired_cache():
        """Clean up expired cache entries."""
        pass
    
    @staticmethod
    def clear_analysis_cache(user_id=None, older_than_days=None):
        """
        Clear the email analysis cache
        
        Args:
            user_id (str): If provided, only clear cache for this user
            older_than_days (int): If provided, only clear cache entries older than this many days
            
        Returns:
            int: Number of cache entries deleted
        """
        logger.info(f"Clearing analysis cache for user: {user_id}, older than {older_than_days} days")
        return 0
    
    @staticmethod
    def ensure_cache_indexes():
        """Ensure cache indexes exist."""
        logger.info("Ensuring cache indexes")
        return True
    
    @staticmethod
    def schedule_cache_cleanup():
        """Schedule cache cleanup task."""
        def cleanup():
            while True:
                try:
                    EmailService._cleanup_expired_cache()
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {str(e)}")
                time.sleep(3600)  # Run every hour

        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start() 