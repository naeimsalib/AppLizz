import os
import base64
import json
import re
import requests
import imaplib
import email
from email.header import decode_header
import ssl
from datetime import datetime, timedelta
import logging
import time
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from job_app_tracker.config.mongodb import mongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import openai  # Add OpenAI import
import html2text
from flask import current_app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_app_tracker/logs/email_scan.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('email_service')

# Download NLTK resources if not already downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except:
        print("Warning: Could not download NLTK punkt. Email content analysis may be limited.")
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        nltk.download('stopwords', quiet=True)
    except:
        print("Warning: Could not download NLTK stopwords. Email content analysis may be limited.")

# Constants
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
OUTLOOK_SCOPES = ['offline_access', 'Mail.Read']
YAHOO_IMAP_SERVER = 'imap.mail.yahoo.com'
YAHOO_IMAP_PORT = 993

# Keywords for job application detection
APPLICATION_KEYWORDS = [
    # General job application keywords
    'application', 'job', 'position', 'resume', 'cv', 'candidate', 'opportunity',
    'interview', 'hiring', 'recruitment', 'talent', 'career', 'employment',
    
    # Application confirmation keywords
    'thank you for applying', 'application has been received', 'application received',
    'job submission', 'application confirmation', 'we have received your application',
    'submission received', 'thank you for your interest', 'application submitted',
    'we have received your resume', 'thank you for submitting', 'application complete',
    'successfully applied', 'application has been submitted', 'thank you for your application',
    
    # Job role indicators
    'role', 'job posting', 'career opportunity', 'job description', 'job requisition',
    'job title', 'job opening', 'job vacancy', 'job id', 'req id', 'requisition',
    
    # Process keywords
    'update', 'feedback', 'next steps', 'follow up', 'status', 'application status',
    'assessment', 'coding challenge', 'technical interview', 'phone screen',
    'background check', 'reference check', 'offer letter', 'decision',
    
    # Interview keywords
    'schedule an interview', 'interview invitation', 'interview request',
    'interview confirmation', 'interview schedule', 'interview details',
    'interview with', 'invite you to interview', 'interview process',
    
    # Rejection keywords
    'unfortunately', 'not selected', 'not moving forward', 'not proceeding',
    'other candidates', 'not a match', 'position has been filled',
    
    # Offer keywords
    'job offer', 'offer letter', 'pleased to offer', 'formal offer',
    'compensation', 'salary', 'benefits', 'start date', 'onboarding',
    
    # Company names of popular job boards and recruiting companies
    'linkedin', 'indeed', 'glassdoor', 'ziprecruiter', 'monster', 'careerbuilder',
    'dice', 'hired', 'angellist', 'wellfound', 'lever', 'greenhouse', 'workday',
    'jobvite', 'smartrecruiters', 'taleo', 'applicant tracking', 'ats',
    
    # Additional job application phrases
    'your application for', 'regarding your application', 'application to', 
    'applied for', 'your candidacy', 'your interest in', 'your resume for',
    'your profile matches', 'job alert', 'job match', 'job opportunity',
    'consider you for', 'consider your application', 'reviewing your application',
    'reviewing your resume', 'reviewing your profile', 'reviewing your candidacy',
    'application process', 'hiring process', 'recruitment process',
    'job search', 'job seeker', 'job hunter', 'job application status'
]

# Keywords for status detection - expanded with more specific phrases
STATUS_KEYWORDS = {
    'applied': [
        'received', 'submitted', 'confirm', 'application', 'received', 'thank you for applying',
        'application has been received', 'application confirmation', 'we have received your application',
        'submission received', 'thank you for your interest', 'application submitted',
        'we have received your resume', 'thank you for submitting', 'application complete',
        'successfully applied', 'application has been submitted', 'thank you for your application',
        'confirmation of your application', 'application acknowledgment', 'we confirm receipt'
    ],
    'in_progress': [
        'reviewing', 'under review', 'being considered', 'in consideration', 'processing',
        'application is being reviewed', 'currently reviewing', 'assessment', 'evaluation',
        'screening', 'pre-screening', 'application process', 'next steps',
        'under consideration', 'being reviewed', 'initial review', 'preliminary review',
        'application is in progress', 'moving forward with your application',
        'coding challenge', 'technical assessment', 'skills assessment', 'online assessment',
        'take-home assignment', 'questionnaire', 'additional information needed'
    ],
    'interview': [
        'interview', 'meet', 'discuss', 'conversation', 'schedule', 'availability',
        'interview details', 'interview appointment', 'arrange an interview', 'phone interview',
        'video interview', 'in-person interview', 'meeting', 'confirm interview',
        'interview invitation', 'would like to speak with you', 'interview process',
        'schedule a time', 'virtual interview', 'zoom interview', 'teams meeting',
        'google meet', 'phone screen', 'technical interview', 'hiring manager',
        'panel interview', 'second interview', 'final interview', 'follow-up interview',
        'interview with the team', 'meet the team', 'interview confirmation'
    ],
    'rejected': [
        'unfortunately', 'not selected', 'other candidates', 'not moving forward', 
        'not proceeding', 'regret', 'we will be going with other candidates', 
        'not a fit', 'regret to inform you', 'move forward with other candidates',
        'application not successful', 'decline', 'rejection', 'thank you for your interest, but',
        'we have decided', 'we have chosen', 'we have filled', 'position has been filled',
        'decided not to proceed', 'pursuing other candidates', 'not successful',
        'we are unable to offer', 'we cannot offer', 'we regret to inform you',
        'after careful consideration', 'we appreciate your interest, however',
        'we have identified candidates', 'we will not be proceeding'
    ],
    'offer': [
        'offer', 'congratulations', 'pleased to inform', 'welcome', 'join our team', 
        'compensation', 'salary', 'benefits', 'start date', 'onboarding',
        'formal offer', 'job offer', 'offer letter', 'employment agreement',
        'we are delighted', 'we are pleased', 'we would like to offer',
        'offer of employment', 'employment offer', 'offer details',
        'accept the offer', 'offer acceptance', 'employment contract',
        'starting salary', 'compensation package', 'benefits package',
        'contingent offer', 'conditional offer', 'official offer'
    ]
}

# Initialize OpenAI API
# Use OpenAI's GPT-3.5-Turbo for premium users
openai_api_key = os.environ.get("OPENAI_API_KEY", "")

# Set up TTL index for analysis_cache collection (expires after 30 days)
try:
    # Create TTL index if it doesn't exist
    if 'created_at_1' not in mongo.db.analysis_cache.index_information():
        mongo.db.analysis_cache.create_index(
            [("created_at", 1)], 
            expireAfterSeconds=30*24*60*60,  # 30 days
            background=True
        )
        logger.info("Created TTL index on analysis_cache collection")
except Exception as e:
    logger.error(f"Error creating TTL index: {str(e)}")

# Initialize the OpenAI client
try:
    # Import the necessary modules
    import httpx
    
    # Create a custom httpx client with appropriate timeouts
    http_client = httpx.Client(
        timeout=30.0,
        follow_redirects=True
    )
    
    # Create the OpenAI client
    openai_client = openai.OpenAI(
        api_key=openai_api_key,
        http_client=http_client
    )
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    openai_client = None

class EmailService:
    @staticmethod
    def get_gmail_auth_url(user_id):
        """Generate Gmail OAuth URL"""
        client_config = {
            "web": {
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.environ.get("GOOGLE_REDIRECT_URI")]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI")
        )
        
        # Store state in session or database
        state = base64.urlsafe_b64encode(user_id.encode()).decode()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'
        )
        
        return auth_url
    
    @staticmethod
    def handle_gmail_callback(code, state):
        """Handle Gmail OAuth callback"""
        # Decode user_id from state
        user_id = base64.urlsafe_b64decode(state.encode()).decode()
        
        client_config = {
            "web": {
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [os.environ.get("GOOGLE_REDIRECT_URI")]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI")
        )
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user email
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        email = profile['emailAddress']
        
        # Store tokens in database
        from job_app_tracker.models.user import User
        user = User.get_by_id(user_id)
        if user:
            expiry = datetime.utcnow() + timedelta(seconds=credentials.expiry)
            user.update_email_connection(
                connected_email=email,
                provider='gmail',
                token=credentials.token,
                refresh_token=credentials.refresh_token,
                expiry=expiry
            )
            return True, user
        
        return False, None
    
    @staticmethod
    def connect_yahoo_imap(user_id, yahoo_email, app_password):
        """Connect to Yahoo Mail using IMAP with app password"""
        try:
            # Create an SSL context with certificate verification
            context = ssl.create_default_context()
            
            # Connect to Yahoo Mail's IMAP server
            mail = imaplib.IMAP4_SSL(YAHOO_IMAP_SERVER, YAHOO_IMAP_PORT, ssl_context=context)
            
            # Try to login
            mail.login(yahoo_email, app_password)
            
            # If login successful, store credentials
            from job_app_tracker.models.user import User
            user = User.get_by_id(user_id)
            
            if user:
                # Store the app password directly (not hashed) for IMAP authentication
                # Set expiry to 1 year from now (app passwords don't expire)
                expiry = datetime.utcnow() + timedelta(days=365)
                
                # Update the user's email connection
                mongo.db.users.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {
                        'email_connected': True,
                        'connected_email': yahoo_email,
                        'email_provider': 'yahoo_imap',
                        'email_token': 'imap_auth',  # Placeholder
                        'email_refresh_token': None,
                        'email_token_expiry': expiry,
                        'email_password': app_password  # Store the actual password for IMAP
                    }}
                )
                
                # Update local attributes
                user.email_connected = True
                user.connected_email = yahoo_email
                user.email_provider = 'yahoo_imap'
                user.email_token = 'imap_auth'
                user.email_refresh_token = None
                user.email_token_expiry = expiry
                user.email_password = app_password  # Add this attribute
                
                # Close the connection
                mail.logout()
                
                return True, user
            
            return False, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def scan_emails(user):
        """
        Scan user's emails for job applications
        Returns a tuple of (success, message, redirect_url)
        """
        # Check if email is connected
        if not user.email_connected:
            return False, "Email not connected. Please connect an email account first.", "main.settings"
        
        # Check if user is premium - PREMIUM ONLY FEATURE
        if not user.is_premium:
            return False, "Email scanning is a premium feature. Please upgrade to premium.", "main.settings"
        
        # Check if email provider is specified
        if not hasattr(user, 'email_provider') or not user.email_provider:
            return False, "Email provider not specified. Please reconnect your email account.", "main.settings"
        
        # Check if we've scanned recently (within the last minute for testing purposes)
        if hasattr(user, 'email_settings') and user.email_settings and user.email_settings.get('last_scan'):
            last_scan = user.email_settings.get('last_scan')
            if isinstance(last_scan, str):
                try:
                    last_scan = datetime.fromisoformat(last_scan)
                except ValueError:
                    last_scan = None
            
            if last_scan and (datetime.now() - last_scan).total_seconds() < 60:
                return False, "Emails were scanned recently. Please try again in a minute.", "main.email_suggestions"
        
        # Determine which email provider to use and scan accordingly
        if user.email_provider == 'gmail':
            logger.info(f"Scanning Gmail for user {user.id}")
            success, job_applications = EmailService._scan_gmail(user)
        elif user.email_provider == 'yahoo_imap':
            logger.info(f"Scanning Yahoo Mail for user {user.id}")
            success, job_applications = EmailService._scan_yahoo_imap(user)
        elif user.email_provider == 'outlook':
            logger.info(f"Scanning Outlook for user {user.id}")
            success, job_applications = EmailService._scan_outlook(user)
        else:
            logger.error(f"Unsupported email provider: {user.email_provider}")
            return False, f"Unsupported email provider: {user.email_provider}. Please reconnect with Gmail, Yahoo, or Outlook.", "main.settings"
        
        if not success:
            logger.error(f"Email scan failed: {job_applications}")
            return False, job_applications, "main.email_suggestions"  # In this case, job_applications contains the error message
        
        # Update last scan time
        if hasattr(user, 'email_settings') and user.email_settings:
            email_settings = user.email_settings.copy()
        else:
            email_settings = {}
        
        email_settings['last_scan'] = datetime.now()
        
        # Update user settings
        mongo.db.users.update_one(
            {'_id': ObjectId(user.id)},
            {'$set': {'email_settings': email_settings}}
        )
        
        # Process applications
        if job_applications:
            suggestions_count = EmailService._process_applications(user, job_applications)
            logger.info(f"Found {len(job_applications)} job application emails, created {suggestions_count} suggestions")
            return True, f"Found {len(job_applications)} potential job application emails", "main.email_suggestions"
        else:
            logger.info(f"No job application emails found for user {user.id}")
            return True, "No job application emails found", "main.email_suggestions"
    
    @staticmethod
    def _get_gmail_credentials(user):
        """
        Get Gmail credentials for the user
        Returns a Credentials object or None if credentials are invalid
        """
        try:
            # Check if user has Gmail credentials
            if not hasattr(user, 'email_token') or not user.email_token:
                logger.error(f"User {user.id} has no Gmail token")
                return None
                
            if not hasattr(user, 'email_refresh_token') or not user.email_refresh_token:
                logger.error(f"User {user.id} has no Gmail refresh token")
                return None
            
            # Create credentials object
            credentials = Credentials(
                token=user.email_token,
                refresh_token=user.email_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ.get("GOOGLE_CLIENT_ID"),
                client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
                scopes=GMAIL_SCOPES
            )
            
            # Check if token is expired and refresh if needed
            if hasattr(user, 'email_token_expiry') and user.email_token_expiry:
                if isinstance(user.email_token_expiry, str):
                    try:
                        expiry = datetime.fromisoformat(user.email_token_expiry)
                    except ValueError:
                        expiry = None
                else:
                    expiry = user.email_token_expiry
                
                if expiry and expiry < datetime.utcnow():
                    logger.info(f"Refreshing expired Gmail token for user {user.id}")
                    credentials.refresh(requests.Request())
                    
                    # Update tokens in database
                    mongo.db.users.update_one(
                        {'_id': ObjectId(user.id)},
                        {'$set': {
                            'email_token': credentials.token,
                            'email_refresh_token': credentials.refresh_token,
                            'email_token_expiry': datetime.utcnow() + timedelta(seconds=credentials.expiry)
                        }}
                    )
            
            return credentials
            
        except Exception as e:
            logger.error(f"Error getting Gmail credentials for user {user.id}: {str(e)}")
            return None

    @staticmethod
    def _scan_gmail(user):
        """
        Scan Gmail for job application emails
        Returns a tuple of (success, job_applications or error_message)
        """
        try:
            # Get credentials
            creds = EmailService._get_gmail_credentials(user)
            if not creds:
                return False, "Gmail credentials not found or expired. Please reconnect your Gmail account."
            
            # Build the Gmail API service
            service = build('gmail', 'v1', credentials=creds)
            
            # Get messages from the last day only (for testing purposes)
            one_day_ago = (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')
            query = f'after:{one_day_ago}'
            
            # Execute the API request
            results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return True, []  # No emails found
            
            job_applications = []
            
            # Process each message
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                
                # Extract headers
                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
                
                # Parse date
                email_date = EmailService._parse_email_date(date_str) if date_str else datetime.now()
                
                # Extract body
                body = EmailService._get_email_body(msg['payload'])
                
                # Analyze email
                analysis = EmailService._analyze_email_with_ai(user, subject, body, from_email)
                
                # If job-related, add to list
                if analysis['is_job_related']:
                    job_applications.append({
                        'email_id': message['id'],
                        'subject': subject,
                        'from_email': from_email,
                        'date': email_date,
                        'company': analysis['company'],
                        'position': analysis['position'],
                        'status': analysis['status'],
                        'job_url': analysis.get('job_url', ''),
                        'deadline': analysis.get('deadline', None),
                        'notes': analysis.get('notes', ''),
                        'reasoning': analysis.get('reasoning', '')
                    })
            
            return True, job_applications
            
        except Exception as e:
            logger.error(f"Error scanning Gmail for user {user.id}: {str(e)}")
            return False, f"Error scanning Gmail: {str(e)}"
    
    @staticmethod
    def _scan_yahoo_imap(user):
        """
        Scan Yahoo Mail via IMAP for job application emails
        Returns a tuple of (success, job_applications or error_message)
        """
        mail = None
        try:
            # Get credentials
            if not hasattr(user, 'email_password') or not user.email_password:
                logger.error(f"Yahoo Mail credentials not found for user {user.id}")
                return False, "Yahoo Mail credentials not found. Please reconnect your Yahoo Mail account."
                
            app_password = user.email_password
            logger.info(f"Retrieved app password for user {user.id}")
            
            yahoo_email = user.connected_email
            if not yahoo_email:
                logger.error(f"Yahoo Mail email address not found for user {user.id}")
                return False, "Yahoo Mail email address not found. Please reconnect your Yahoo Mail account."
            
            logger.info(f"Attempting to connect to Yahoo IMAP server for {yahoo_email}")
            
            # Connect to Yahoo IMAP server
            mail = imaplib.IMAP4_SSL('imap.mail.yahoo.com')
            logger.info("Successfully created IMAP SSL connection")
            
            # Login to Yahoo Mail
            logger.info(f"Attempting to login with email: {yahoo_email}")
            mail.login(yahoo_email, app_password)
            logger.info("Successfully logged in to Yahoo Mail")
            
            # Select inbox folder
            mail.select('inbox')
            logger.info("Successfully selected inbox folder")
            
            # Search for emails from the last 14 days to find more emails
            fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime("%d-%b-%Y")
            logger.info(f"Searching for emails since {fourteen_days_ago}")
            
            # Use a more targeted search to find job-related emails
            # This helps reduce the number of emails we need to process
            search_criteria = [
                '(SUBJECT "application")',
                '(SUBJECT "job")',
                '(SUBJECT "interview")',
                '(SUBJECT "position")',
                '(SUBJECT "offer")',
                '(SUBJECT "career")',
                '(SUBJECT "opportunity")',
                '(SUBJECT "recruitment")',
                '(SUBJECT "hiring")',
                '(SUBJECT "candidate")',
                '(SUBJECT "resume")',
                '(SUBJECT "cv")',
                '(SUBJECT "thank you")',
                '(SUBJECT "confirmation")',
                '(SUBJECT "applied")',
                '(SUBJECT "recruiter")',
                '(SUBJECT "talent")'
            ]
            
            all_message_ids = set()
            
            # Search for each criteria and collect message IDs
            for criteria in search_criteria:
                search_query = f'(SINCE {fourteen_days_ago}) {criteria}'
                status, messages = mail.search(None, search_query)
                
                if status != 'OK':
                    logger.warning(f"Search failed for criteria: {criteria}")
                    continue
                    
                message_ids = messages[0].split()
                all_message_ids.update([msg_id.decode() for msg_id in message_ids])
                
            # If targeted search didn't find enough emails, fall back to searching all emails
            if len(all_message_ids) < 5:
                logger.info("Targeted search found few emails, falling back to general search")
                status, messages = mail.search(None, f'(SINCE {fourteen_days_ago})')
                
                if status != 'OK':
                    mail.logout()
                    logger.error(f"Failed to search emails: {status}")
                    return False, "Failed to search emails. Please try again later."
                    
                message_ids = messages[0].split()
                all_message_ids = set([msg_id.decode() for msg_id in message_ids])
            
            logger.info(f"Found {len(all_message_ids)} emails in the last 14 days")
            
            # Convert back to list and sort to get most recent first
            message_ids_list = sorted(list(all_message_ids), reverse=True)
            
            # Limit to 50 most recent emails for processing
            if len(message_ids_list) > 50:
                message_ids_list = message_ids_list[:50]
                logger.info(f"Limited to 50 most recent emails")
            
            job_applications = []
            
            # Process each message
            for msg_id in message_ids_list:
                logger.info(f"Processing email with ID: {msg_id}")
                status, msg_data = mail.fetch(msg_id.encode(), '(RFC822)')
                
                if status != 'OK':
                    logger.warning(f"Failed to fetch email with ID {msg_id}: {status}")
                    continue
                
                logger.info(f"Successfully fetched email with ID: {msg_id}")
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                
                # Extract headers
                subject = email_message['Subject'] or 'No Subject'
                from_email = email_message['From'] or 'Unknown Sender'
                date_str = email_message['Date']
                
                logger.info(f"Processing email: Subject: '{subject}', From: {from_email}")
                
                # Parse date
                email_date = EmailService._parse_email_date(date_str) if date_str else datetime.now()
                
                # Extract body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        # Skip attachments
                        if "attachment" in content_disposition:
                            continue
                        
                        # Get text content
                        if content_type == "text/plain" or content_type == "text/html":
                            try:
                                body_part = part.get_payload(decode=True).decode()
                                body += body_part
                            except:
                                pass
                else:
                    # Not multipart - get payload directly
                    try:
                        body = email_message.get_payload(decode=True).decode()
                    except:
                        body = ""
                
                # Convert HTML to plain text if needed
                if "<html" in body.lower():
                    body = html2text.html2text(body)
                
                logger.info(f"Extracted body length: {len(body)} characters")
                
                # Quick pre-check for job-related content to save processing time
                if not any(keyword.lower() in subject.lower() or keyword.lower() in body.lower()[:500] 
                          for keyword in ['job', 'application', 'position', 'interview', 'offer', 'career', 'opportunity']):
                    logger.info(f"Email doesn't appear to be job-related, skipping detailed analysis")
                    continue
                    
                logger.info(f"Email body preview: {body[:200]}...")
                
                # Check for job-related keywords before AI analysis
                keyword_check = EmailService._contains_job_keywords(subject, body)
                logger.info(f"Initial keyword check: {'PASSED' if keyword_check else 'FAILED'}")
                
                if not keyword_check:
                    continue
                
                # Analyze email
                logger.info(f"Analyzing email with AI")
                analysis = EmailService._analyze_email_with_ai(user, subject, body, from_email)
                
                # Log detailed analysis results
                logger.info(f"Analysis results: is_job_related={analysis['is_job_related']}, company={analysis['company']}, position={analysis['position']}, status={analysis['status']}")
                logger.info(f"Analysis reasoning: {analysis.get('reasoning', 'No reasoning provided')}")
                
                # If job-related, add to list
                if analysis['is_job_related']:
                    logger.info(f"Email identified as job-related: {analysis['company']} - {analysis['position']}")
                    job_applications.append({
                        'email_id': msg_id,
                        'subject': subject,
                        'from_email': from_email,
                        'date': email_date,
                        'company': analysis['company'],
                        'position': analysis['position'],
                        'status': analysis['status'],
                        'job_url': analysis.get('job_url', ''),
                        'deadline': analysis.get('deadline', None),
                        'notes': analysis.get('notes', ''),
                        'reasoning': analysis.get('reasoning', '')
                    })
                else:
                    logger.info(f"Email not identified as job-related: {analysis.get('reasoning', 'No reasoning provided')}")
            
            mail.logout()
            logger.info(f"Completed scanning Yahoo Mail. Found {len(job_applications)} job-related emails.")
            return True, job_applications
            
        except Exception as e:
            logger.error(f"Error scanning Yahoo Mail for user {user.id}: {str(e)}")
            # Make sure to close the connection if an error occurs
            if mail:
                try:
                    mail.logout()
                except:
                    pass
            return False, f"Error scanning Yahoo Mail: {str(e)}"
    
    @staticmethod
    def _process_applications(user, job_applications):
        """
        Process job applications found in emails
        Creates suggestions for the user to review
        """
        if not job_applications:
            return 0
        
        # Log the total number of job applications found
        logger.info(f"Processing {len(job_applications)} job applications for user {user.id}")
        
        # Get existing applications for this user
        existing_applications = list(mongo.db.applications.find({'user_id': str(user.id)}))
        
        # Get existing suggestions
        existing_suggestions = mongo.db.email_suggestions.find_one({
            'user_id': str(user.id),
            'processed': False
        })
        
        # Extract existing suggestion details to avoid duplicates
        existing_suggestion_details = set()
        if existing_suggestions:
            for suggestion in existing_suggestions['suggestions']:
                if suggestion['type'] == 'new':
                    # For new applications, use company + position as key
                    key = f"{suggestion['company']}:{suggestion['position']}"
                    existing_suggestion_details.add(key)
                elif suggestion['type'] == 'update':
                    # For updates, use application_id + new_status as key
                    key = f"{suggestion['application_id']}:{suggestion['new_status']}"
                    existing_suggestion_details.add(key)
        
        # Define status priority (higher number = higher priority)
        status_priority = {
            'Applied': 1,
            'In Progress': 2,
            'Interview': 3,
            'Offer': 4,
            'Rejected': 5
        }
        
        suggestions = []
        processed_emails = set()  # Track processed emails to avoid duplicates
        
        # Process each job application
        for job_app in job_applications:
            # Skip if not job-related (double-check)
            if not job_app.get('is_job_related', True):
                continue
            
            # Create a unique identifier for this email to avoid duplicates
            email_id = job_app.get('email_id', '')
            subject = job_app.get('subject', '')
            email_key = f"{email_id}:{subject}"
            
            # Skip if we've already processed this email
            if email_key in processed_emails:
                logger.info(f"Skipping duplicate email: {subject}")
                continue
            
            processed_emails.add(email_key)
            
            company = job_app['company']
            position = job_app['position']
            status = job_app['status']
            
            # Skip if company or position is unknown - we need both for a good suggestion
            if company == "Unknown Company" and position == "Unknown Position":
                logger.info(f"Skipping suggestion with unknown company AND position: {company} - {position}")
                continue
            
            # Prepare notes with application platform if available
            notes = job_app.get('notes', '')
            application_platform = job_app.get('application_platform', '')
            
            if application_platform:
                if notes:
                    notes = f"Applied via {application_platform}. {notes}"
                else:
                    notes = f"Applied via {application_platform}."
            
            # Check if this company exists in user's applications
            matching_apps = [
                app for app in existing_applications 
                if app['company'].lower() == company.lower()
            ]
            
            if matching_apps:
                # If position matches, suggest status update if needed
                position_match_found = False
                for app in matching_apps:
                    # Check for position match with more flexible matching
                    app_position = app.get('position', '').lower() if app.get('position') else ''
                    current_position = position.lower()
                    
                    # Consider it a match if positions are similar (one contains the other)
                    position_match = (
                        app_position in current_position or 
                        current_position in app_position or
                        app_position == current_position
                    )
                    
                    if position_match:
                        position_match_found = True
                        current_status = app.get('status', 'Applied')
                        
                        # Only suggest update if new status has higher priority
                        if (status_priority.get(status, 0) > status_priority.get(current_status, 0)):
                            # Create a unique key for this suggestion
                            suggestion_key = f"{str(app['_id'])}:{status}"
                            
                            # Skip if this suggestion already exists
                            if suggestion_key in existing_suggestion_details:
                                continue
                            
                            # Add to suggestions
                            suggestions.append({
                                'type': 'update',
                                'application_id': str(app['_id']),
                                'company': company,
                                'position': app.get('position', position),
                                'current_status': current_status,
                                'new_status': status,
                                'email_subject': job_app['subject'],
                                'date': job_app['date'],
                                'reasoning': job_app.get('reasoning', ''),
                                'application_platform': application_platform,
                                'notes': notes
                            })
                            
                            # Add to existing suggestions set to avoid duplicates
                            existing_suggestion_details.add(suggestion_key)
                            break
                
                # If no position match was found, suggest as a new application
                if not position_match_found:
                    suggestion_key = f"{company}:{position}"
                    
                    # Skip if this suggestion already exists
                    if suggestion_key in existing_suggestion_details:
                        continue
                    
                    # Add to suggestions
                    suggestions.append({
                        'type': 'new',
                        'company': company,
                        'position': position,
                        'status': status,
                        'email_subject': job_app['subject'],
                        'date': job_app['date'],
                        'job_url': job_app.get('job_url', ''),
                        'deadline': job_app.get('deadline', None),
                        'notes': notes,
                        'reasoning': job_app.get('reasoning', ''),
                        'application_platform': application_platform
                    })
                    
                    # Add to existing suggestions set to avoid duplicates
                    existing_suggestion_details.add(suggestion_key)
            else:
                # Suggest new application
                suggestion_key = f"{company}:{position}"
                
                # Skip if this suggestion already exists
                if suggestion_key in existing_suggestion_details:
                    continue
                
                # Add to suggestions
                suggestions.append({
                    'type': 'new',
                    'company': company,
                    'position': position,
                    'status': status,
                    'email_subject': job_app['subject'],
                    'date': job_app['date'],
                    'job_url': job_app.get('job_url', ''),
                    'deadline': job_app.get('deadline', None),
                    'notes': notes,
                    'reasoning': job_app.get('reasoning', ''),
                    'application_platform': application_platform
                })
                
                # Add to existing suggestions set to avoid duplicates
                existing_suggestion_details.add(suggestion_key)
        
        # If we have suggestions, store them
        if suggestions:
            if existing_suggestions:
                # Append to existing suggestions
                mongo.db.email_suggestions.update_one(
                    {'_id': existing_suggestions['_id']},
                    {'$push': {'suggestions': {'$each': suggestions}}}
                )
            else:
                # Create new suggestions document
                mongo.db.email_suggestions.insert_one({
                    'user_id': str(user.id),
                    'suggestions': suggestions,
                    'processed': False,
                    'created_at': datetime.utcnow()
                })
            
            logger.info(f"Created {len(suggestions)} suggestions out of {len(job_applications)} job applications for user {user.id}")
        else:
            logger.info(f"No new suggestions created from {len(job_applications)} job applications for user {user.id}")
        
        return len(suggestions)
    
    @staticmethod
    def _scan_outlook(user):
        """Scan Outlook for job applications"""
        # Implementation for Outlook would go here
        return False, "Outlook integration not implemented yet"
    
    @staticmethod
    def _get_email_body(payload):
        """Extract email body from payload"""
        body = ""
        
        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    soup = BeautifulSoup(html, 'html.parser')
                    body = soup.get_text()
                    break
                elif 'parts' in part:
                    # Recursive call for multipart emails
                    body = EmailService._get_email_body(part)
                    if body:
                        break
        
        return body
    
    @staticmethod
    def _is_job_related(subject, body):
        """
        Check if email is job-related using enhanced keyword detection
        This is a FALLBACK method for premium users when AI analysis fails
        """
        combined_text = (subject + " " + body).lower()
        
        # Check for job-related keywords
        keyword_count = 0
        matched_keywords = []
        
        for keyword in APPLICATION_KEYWORDS:
            if keyword.lower() in combined_text:
                keyword_count += 1
                matched_keywords.append(keyword)
                
                # If we find a strong indicator phrase (multi-word), give it more weight
                if len(keyword.split()) > 1:
                    keyword_count += 1
        
        # Check for status-specific keywords which also indicate job-relatedness
        for status, keywords in STATUS_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in combined_text and keyword not in matched_keywords:
                    keyword_count += 1
                    matched_keywords.append(keyword)
                    
                    # If we find a strong indicator phrase (multi-word), give it more weight
                    if len(keyword.split()) > 1:
                        keyword_count += 0.5
        
        # Log the matched keywords for debugging
        if keyword_count > 0:
            logger.debug(f"Job-related keywords found: {matched_keywords}")
        
        # If multiple keywords found, likely job-related
        # Higher threshold for single-word matches, lower for multi-word phrases
        return keyword_count >= 2
    
    @staticmethod
    def _extract_company(from_email, subject, body):
        """Extract company name from email"""
        # Try to extract from email domain
        domain_match = re.search(r'@([^.]+)', from_email)
        if domain_match:
            domain = domain_match.group(1)
            if domain not in ['gmail', 'yahoo', 'hotmail', 'outlook', 'aol', 'icloud']:
                return domain.title()
        
        # Try to extract from signature or common patterns
        company_patterns = [
            r'(?:from|at|with)\s+([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Corp|Corporation|Company))',
            r'([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Corp|Corporation|Company))',
            r'(?:team|recruiting|talent|hr)(?:\s+at)?\s+([A-Z][A-Za-z0-9\s&]+)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, body)
            if match:
                return match.group(1).strip()
        
        # Default to domain if nothing else found
        email_parts = from_email.split('@')
        if len(email_parts) > 1:
            domain = email_parts[1].split('.')[0]
            return domain.title()
        
        return "Unknown Company"
    
    @staticmethod
    def _extract_position(subject, body):
        """Extract position from email"""
        # Common patterns for job positions
        position_patterns = [
            r'(?:position|role|job|opportunity)(?:\s+for)?\s+(?:of\s+)?([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant))',
            r'([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant))\s+(?:position|role|job|opportunity)',
            r'(?:applying|application|candidacy)\s+for\s+([A-Za-z0-9\s]+)'
        ]
        
        # Check subject first
        for pattern in position_patterns:
            match = re.search(pattern, subject)
            if match:
                return match.group(1).strip()
        
        # Then check body
        for pattern in position_patterns:
            match = re.search(pattern, body)
            if match:
                return match.group(1).strip()
        
        return "Unknown Position"
    
    @staticmethod
    def _determine_status(subject, body):
        """
        Determine application status from email content with enhanced keyword detection
        """
        combined_text = (subject + " " + body).lower()
        
        # Check for each status type
        status_scores = {}
        
        for status, keywords in STATUS_KEYWORDS.items():
            # Count keyword matches
            base_score = sum(1 for keyword in keywords if keyword.lower() in combined_text)
            
            # Give extra weight to multi-word phrases as they're more specific
            phrase_bonus = sum(0.5 for keyword in keywords 
                              if len(keyword.split()) > 1 and keyword.lower() in combined_text)
            
            status_scores[status] = base_score + phrase_bonus
        
        # Get status with highest score
        if status_scores:
            max_status = max(status_scores.items(), key=lambda x: x[1])
            if max_status[1] > 0:
                # Map internal status to application status
                status_mapping = {
                    'applied': 'Applied',
                    'in_progress': 'In Progress',
                    'interview': 'Interview',
                    'rejected': 'Rejected',
                    'offer': 'Offer'
                }
                return status_mapping.get(max_status[0], 'Applied')
        
        # Default to Applied if no clear status
        return 'Applied'
    
    @staticmethod
    def _parse_email_date(date_str):
        """Parse email date string to datetime"""
        try:
            # Handle various date formats
            formats = [
                '%a, %d %b %Y %H:%M:%S %z',
                '%d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S',
                '%d %b %Y %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Default to current time if parsing fails
            return datetime.utcnow()
        except:
            return datetime.utcnow()

    @staticmethod
    def _analyze_email_with_ai(user, subject, body, from_email):
        """
        Analyze email content using OpenAI GPT-3.5-Turbo to extract job application information
        This is a PREMIUM ONLY feature with fallback to traditional methods if AI fails
        Returns a dictionary with company, position, status, and is_job_related
        """
        # This method should only be called for premium users, but double-check
        if not user.is_premium:
            logger.warning(f"Non-premium user {user.id} attempted to use AI email analysis")
            return EmailService._analyze_with_traditional_methods(subject, body, from_email)
        
        # Check if OpenAI client is available
        if not openai_api_key or openai_client is None:
            logger.warning("OpenAI API key or client not available, falling back to traditional analysis")
            return EmailService._analyze_with_traditional_methods(subject, body, from_email)
        
        # FIRST FILTER: Check if email contains job-related keywords before sending to AI
        # This saves API costs and improves accuracy by only analyzing relevant emails
        if not EmailService._contains_job_keywords(subject, body):
            logger.info(f"Email from {from_email} with subject '{subject[:30]}...' doesn't contain job keywords, skipping AI analysis")
            return {
                'is_job_related': False,
                'company': "Unknown Company",
                'position': "Unknown Position",
                'status': "Applied",
                'reasoning': "Email does not contain sufficient job application keywords."
            }
        
        # Filter out assessment confirmations that aren't actual job applications
        if "assessment" in subject.lower() and "submit" in body.lower() and "answer" in body.lower():
            logger.info(f"Email appears to be an assessment confirmation, not a job application: {subject}")
            return {
                'is_job_related': False,
                'company': "Unknown Company",
                'position': "Unknown Position",
                'status': "Applied",
                'reasoning': "Email appears to be an assessment confirmation, not a job application."
            }
        
        # Pre-process LinkedIn job applications
        application_platform = None
        
        # Check if this is a LinkedIn job application
        if "linkedin" in from_email.lower() and ("application" in subject.lower() or "applied" in subject.lower()):
            application_platform = "LinkedIn"
            
            # Extract company and position from LinkedIn emails
            company_match = re.search(r'at\s+([^,]+)', subject)
            position_match = re.search(r'for\s+([^,]+?)(?:\s+at|$)', subject)
            
            # If we found both company and position, we can skip AI analysis
            if company_match and position_match:
                company = company_match.group(1).strip()
                position = position_match.group(1).strip()
                
                logger.info(f"LinkedIn application detected: {position} at {company}")
                
                # Extract job URL if present - but don't include problematic characters
                job_url = ""
                url_match = re.search(r'https://www\.linkedin\.com/comm/jobs/view/([^\s&]+)', body)
                if url_match:
                    job_url = f"https://www.linkedin.com/jobs/view/{url_match.group(1).split('?')[0]}"
                
                return {
                    'is_job_related': True,
                    'company': company,
                    'position': position,
                    'status': "Applied",
                    'job_url': job_url,
                    'application_platform': application_platform,
                    'reasoning': f"LinkedIn job application confirmation for {position} at {company}"
                }
        
        # Check for other job platforms
        elif "indeed" in from_email.lower() and ("application" in subject.lower() or "applied" in subject.lower()):
            application_platform = "Indeed"
        elif "ziprecruiter" in from_email.lower():
            application_platform = "ZipRecruiter"
        elif "glassdoor" in from_email.lower():
            application_platform = "Glassdoor"
        elif "monster" in from_email.lower():
            application_platform = "Monster"
        elif "dice" in from_email.lower():
            application_platform = "Dice"
        elif "careerbuilder" in from_email.lower():
            application_platform = "CareerBuilder"
        elif "lever.co" in from_email.lower() or "lever.co" in body.lower():
            application_platform = "Lever"
        elif "greenhouse.io" in from_email.lower() or "greenhouse.io" in body.lower():
            application_platform = "Greenhouse"
        elif "workday" in from_email.lower() or "workday" in body.lower():
            application_platform = "Workday"
        elif "smartrecruiters" in from_email.lower() or "smartrecruiters" in body.lower():
            application_platform = "SmartRecruiters"
        elif "taleo" in from_email.lower() or "taleo" in body.lower():
            application_platform = "Taleo"
        
        # Generate a more robust cache key based on email content
        # Use a combination of from_email, subject, and a hash of the first part of the body
        # This makes the cache key more unique and less prone to collisions
        email_hash = hash(from_email + subject + body[:100])
        cache_key = f"email_analysis:{email_hash}"
        
        # Try to find in cache
        try:
            cached_result = mongo.db.analysis_cache.find_one({"_id": cache_key})
            if cached_result:
                logger.info(f"Using cached analysis result for email from {from_email}")
                result = {
                    'is_job_related': cached_result['is_job_related'],
                    'company': cached_result['company'],
                    'position': cached_result['position'],
                    'status': cached_result['status'],
                    'reasoning': cached_result.get('reasoning', ''),
                    'job_url': cached_result.get('job_url', ''),
                    'deadline': cached_result.get('deadline', None)
                }
                
                # Add application platform if we detected it
                if application_platform and 'application_platform' not in result:
                    result['application_platform'] = application_platform
                
                return result
        except Exception as cache_error:
            logger.warning(f"Error retrieving from cache: {str(cache_error)}")
        
        try:
            # Prepare a concise, focused prompt for OpenAI
            system_prompt = """You are a job application email analyzer. Your task is to determine if an email is related to a job application process and extract key information.

Be inclusive in your analysis. Identify emails that might be part of a job application process:
- Application confirmations
- Interview invitations
- Rejection notices
- Job offers
- Application status updates
- Recruiter emails about specific positions
- Job board notifications about applications
- Networking emails that mention specific job opportunities

DO NOT classify as job-related:
- Assessment confirmations that don't mention specific job positions
- General newsletters without specific job mentions
- Promotional emails unrelated to jobs
- Emails about general career events without specific job mentions

FOCUS ON EXTRACTING these critical fields:
1. Company name - Extract the exact company name the user applied to (not the job platform)
2. Job title/position - Extract the exact job title the user applied for
3. Application status - Determine if Applied, In Progress, Interview, Offer, or Rejected
4. Application platform - Identify the platform used to apply (LinkedIn, Indeed, ZipRecruiter, etc.)

For LinkedIn job application emails, be careful to extract the actual company name, not LinkedIn itself.
For job board emails, extract the actual employer company, not the job board name."""

            # Sanitize inputs to prevent JSON parsing errors
            safe_subject = subject.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
            safe_from = from_email.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
            
            # Truncate and sanitize body to prevent JSON errors
            truncated_body = body[:1500]
            safe_body = truncated_body.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
            
            user_prompt = f"""Analyze this email and extract job application information.

Email Subject: {safe_subject}
From: {safe_from}
Email Body: {safe_body}

Return a JSON object with these fields:
{{
    "is_job_related": true/false,
    "company": "Company Name",
    "position": "Job Title",
    "status": "Applied/In Progress/Interview/Offer/Rejected",
    "job_url": "URL if present (without special characters)",
    "application_platform": "Platform used to apply (LinkedIn, Indeed, etc.)",
    "deadline": "Application deadline if mentioned (YYYY-MM-DD)",
    "notes": "Brief 1-2 line summary of important details",
    "confidence": 0-100
}}

Set is_job_related to true if you're reasonably confident (>70%) this is about a job application.
If not job-related, just return is_job_related: false with confidence.
IMPORTANT: For job_url, only include the base URL without query parameters to avoid parsing errors."""
            
            # Call OpenAI API
            response = openai_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-3.5-turbo",
                temperature=0.1,  # Lower temperature for more consistent results
                max_tokens=300,
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            # Parse the response
            try:
                result = json.loads(response.choices[0].message.content)
                
                # Validate and sanitize the result
                if not isinstance(result, dict):
                    raise ValueError("Invalid response format")
                
                # Only consider as job-related if confidence is high
                is_job_related = bool(result.get('is_job_related', False))
                confidence = result.get('confidence', 0)
                
                # If confidence is provided and below threshold, mark as not job-related
                # Lowered threshold from 85 to 70 to be more inclusive
                if 'confidence' in result and confidence < 70:
                    is_job_related = False
                
                # Extract and sanitize fields
                company = result.get('company') if result.get('company') not in [None, "null", ""] else "Unknown Company"
                position = result.get('position') if result.get('position') not in [None, "null", ""] else "Unknown Position"
                status = result.get('status')
                
                # Validate status
                valid_statuses = ["Applied", "In Progress", "Interview", "Rejected", "Offer"]
                if status not in valid_statuses:
                    status = "Applied"  # Default to Applied if invalid status
                
                # Extract additional fields
                job_url = result.get('job_url', '')
                # Clean up job URL to avoid JSON parsing errors
                if job_url and isinstance(job_url, str):
                    # Remove query parameters from LinkedIn URLs to avoid parsing issues
                    if "linkedin.com" in job_url.lower():
                        job_url = job_url.split('?')[0]
                else:
                    job_url = ""
                
                notes = result.get('notes') if result.get('notes') not in [None, "null", ""] else ""
                
                # Extract application platform if detected by AI
                detected_platform = result.get('application_platform')
                if detected_platform and detected_platform not in [None, "null", ""]:
                    application_platform = detected_platform
                
                # Parse deadline if present
                deadline = None
                if result.get('deadline') and result.get('deadline') not in ["null", ""]:
                    try:
                        deadline = datetime.strptime(result.get('deadline'), '%Y-%m-%d')
                    except (ValueError, TypeError):
                        deadline = None
                
                analysis_result = {
                    'is_job_related': is_job_related,
                    'company': company,
                    'position': position,
                    'status': status,
                    'job_url': job_url,
                    'deadline': deadline,
                    'notes': notes,
                    'reasoning': f"Confidence: {confidence}%. {notes}"
                }
                
                # Add application platform if detected
                if application_platform:
                    analysis_result['application_platform'] = application_platform
                
                # Cache the result - use update_one with upsert instead of insert_one to avoid duplicate key errors
                try:
                    cache_data = {
                        "user_id": str(user.id),
                        "is_job_related": analysis_result['is_job_related'],
                        "company": analysis_result['company'],
                        "position": analysis_result['position'],
                        "status": analysis_result['status'],
                        "job_url": analysis_result['job_url'],
                        "deadline": analysis_result['deadline'],
                        "notes": analysis_result.get('notes', ''),
                        "reasoning": analysis_result.get('reasoning', ''),
                        "email_from": from_email,
                        "email_subject": subject[:100],
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    # Add application platform to cache if detected
                    if application_platform:
                        cache_data["application_platform"] = application_platform
                    
                    mongo.db.analysis_cache.update_one(
                        {"_id": cache_key},
                        {"$set": cache_data},
                        upsert=True
                    )
                    logger.info(f"Cached analysis result for email from {from_email}")
                except Exception as cache_error:
                    # Log the error but continue with the analysis
                    logger.warning(f"Error caching analysis result: {str(cache_error)}")
                
                return analysis_result
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON parsing error: {str(json_error)}")
                logger.error(f"Raw response: {response.choices[0].message.content}")
                return EmailService._analyze_with_traditional_methods(subject, body, from_email)
            
        except Exception as e:
            # Log the error
            logger.error(f"Error in AI analysis: {str(e)}")
            # Fall back to traditional methods
            logger.info("Falling back to traditional analysis due to AI error")
            return EmailService._analyze_with_traditional_methods(subject, body, from_email)
    
    @staticmethod
    def _contains_job_keywords(subject, body):
        """
        Check if the email contains job-related keywords
        This is a pre-filter before sending to AI to save API costs
        """
        combined_text = (subject + " " + body[:1000]).lower()  # Only check first 1000 chars for efficiency
        
        # Check for job-related keywords
        keyword_count = 0
        matched_keywords = []
        
        # First check for strong indicators - multi-word phrases that strongly indicate job applications
        strong_indicators = [
            'thank you for applying', 'application has been received', 'application received',
            'we have received your application', 'application submitted', 'thank you for your application',
            'schedule an interview', 'interview invitation', 'job offer', 'offer letter',
            'your application for', 'regarding your application', 'application to',
            'your candidacy', 'your interest in', 'consider your application'
        ]
        
        for indicator in strong_indicators:
            if indicator.lower() in combined_text:
                # If we find a strong indicator, immediately consider it job-related
                logger.info(f"Strong job indicator found: {indicator}")
                return True
        
        # Check for company names in the from_email domain that might indicate job applications
        job_board_domains = [
            'linkedin', 'indeed', 'glassdoor', 'ziprecruiter', 'monster', 'careerbuilder',
            'dice', 'hired', 'angellist', 'wellfound', 'lever', 'greenhouse', 'workday',
            'jobvite', 'smartrecruiters', 'taleo', 'applicanttracking', 'recruiter', 'talent'
        ]
        
        # Check for regular keywords
        for keyword in APPLICATION_KEYWORDS:
            if keyword.lower() in combined_text:
                keyword_count += 1
                matched_keywords.append(keyword)
                
                # If we find a strong indicator phrase (multi-word), give it more weight
                if len(keyword.split()) > 1:
                    keyword_count += 1
        
        # Check for status-specific keywords which also indicate job-relatedness
        for status, keywords in STATUS_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in combined_text and keyword not in matched_keywords:
                    keyword_count += 1
                    matched_keywords.append(keyword)
                    
                    # If we find a strong indicator phrase (multi-word), give it more weight
                    if len(keyword.split()) > 1:
                        keyword_count += 0.5
        
        # Log the matched keywords for debugging
        if keyword_count > 0:
            logger.info(f"Job-related keywords found: {matched_keywords}")
        else:
            logger.info("No job-related keywords found in email")
        
        # Lower the threshold from 2 to 1 to be more inclusive
        return keyword_count >= 1
    
    @staticmethod
    def _analyze_with_traditional_methods(subject, body, from_email):
        """
        Use traditional keyword-based methods to analyze email
        This is a FALLBACK method for premium users when AI analysis fails
        """
        try:
            logger.info(f"Using traditional analysis for email from {from_email}")
            # Check if email is job-related
            is_job_related = EmailService._is_job_related(subject, body)
            if not is_job_related:
                return {
                    'is_job_related': False,
                    'company': "Unknown Company",
                    'position': "Unknown Position",
                    'status': "Applied",
                    'reasoning': "Email does not contain sufficient job application keywords."
                }
            
            # Extract information
            company = EmailService._extract_company(from_email, subject, body)
            position = EmailService._extract_position(subject, body)
            status = EmailService._determine_status(subject, body)
            
            # Define status mapping
            status_mapping = {
                'applied': 'Applied',
                'in_progress': 'In Progress',
                'interview': 'Interview',
                'rejected': 'Rejected',
                'offer': 'Offer'
            }
            
            # Calculate confidence score based on extracted data quality
            confidence = 0.5  # Base confidence
            if company != "Unknown Company":
                confidence += 0.2
            if position != "Unknown Position":
                confidence += 0.2
                
            # Generate reasoning based on extracted information
            reasoning_parts = []
            if company != "Unknown Company":
                reasoning_parts.append(f"Identified company: {company}")
            if position != "Unknown Position":
                reasoning_parts.append(f"Identified position: {position}")
            
            # Add status reasoning with matched keywords
            matched_status_keywords = []
            for status_name, keywords in STATUS_KEYWORDS.items():
                if status == status_mapping.get(status_name, 'Applied'):
                    matched_status_keywords = [k for k in keywords if k.lower() in subject.lower() or k.lower() in body.lower()]
                    if matched_status_keywords:
                        # Limit to first 3 keywords to keep reasoning concise
                        if len(matched_status_keywords) > 3:
                            matched_status_keywords = matched_status_keywords[:3]
                        reasoning_parts.append(f"Status {status} identified based on keywords: {', '.join(matched_status_keywords)}")
                        break
            
            reasoning = "Analysis based on traditional keyword matching (AI analysis fallback). " + " ".join(reasoning_parts)
            
            return {
                'is_job_related': True,
                'company': company,
                'position': position,
                'status': status,
                'reasoning': reasoning
            }
        except Exception as e:
            # Log the error and return a safe default
            logger.error(f"Error in traditional analysis: {str(e)}")
            return {
                'is_job_related': False,
                'company': "Unknown Company",
                'position': "Unknown Position",
                'status': "Applied",
                'reasoning': f"Error occurred during analysis: {str(e)}"
            }
    
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
        query = {}
        
        # Filter by user if specified
        if user_id:
            query["user_id"] = str(user_id)
        
        # Filter by age if specified
        if older_than_days:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            query["created_at"] = {"$lt": cutoff_date}
        
        try:
            # Delete matching cache entries
            result = mongo.db.analysis_cache.delete_many(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0
    
    @staticmethod
    def ensure_cache_indexes():
        """
        Ensure that the necessary indexes exist on the analysis_cache collection
        This includes a TTL index for automatic expiration of cache entries
        """
        try:
            # Create TTL index on created_at field to automatically expire cache entries after 30 days
            mongo.db.analysis_cache.create_index(
                [("created_at", 1)], 
                expireAfterSeconds=30 * 24 * 60 * 60,  # 30 days in seconds
                background=True
            )
            
            # Create index on user_id for faster queries
            mongo.db.analysis_cache.create_index([("user_id", 1)], background=True)
            
            # Create index on is_job_related for faster filtering
            mongo.db.analysis_cache.create_index([("is_job_related", 1)], background=True)
            
            logger.info("Cache indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating cache indexes: {str(e)}")
    
    @staticmethod
    def schedule_cache_cleanup():
        """
        Schedule a background task to clean up the cache periodically
        This runs in a separate thread to avoid blocking the main application
        """
        import threading
        
        def cleanup_worker():
            """Worker function that runs the cleanup task periodically"""
            while True:
                try:
                    logger.info("Starting scheduled cache cleanup")
                    
                    # Ensure indexes exist - direct MongoDB access without Flask context
                    try:
                        # Create TTL index on created_at field if it doesn't exist
                        if 'created_at_1' not in mongo.db.analysis_cache.index_information():
                            mongo.db.analysis_cache.create_index(
                                [("created_at", 1)], 
                                expireAfterSeconds=30 * 24 * 60 * 60,  # 30 days in seconds
                                background=True
                            )
                        
                        # Create index on user_id for faster queries if it doesn't exist
                        if 'user_id_1' not in mongo.db.analysis_cache.index_information():
                            mongo.db.analysis_cache.create_index([("user_id", 1)], background=True)
                        
                        # Create index on is_job_related for faster filtering if it doesn't exist
                        if 'is_job_related_1' not in mongo.db.analysis_cache.index_information():
                            mongo.db.analysis_cache.create_index([("is_job_related", 1)], background=True)
                        
                        logger.info("Cache indexes verified")
                    except Exception as e:
                        logger.error(f"Error creating cache indexes: {str(e)}")
                    
                    # Clean up old cache entries (older than 30 days)
                    try:
                        cutoff_date_old = datetime.utcnow() - timedelta(days=30)
                        old_result = mongo.db.analysis_cache.delete_many({"created_at": {"$lt": cutoff_date_old}})
                        old_entries_deleted = old_result.deleted_count
                    except Exception as e:
                        logger.error(f"Error cleaning up old cache entries: {str(e)}")
                        old_entries_deleted = 0
                    
                    # Clean up non-job-related entries more aggressively (older than 7 days)
                    try:
                        cutoff_date_non_job = datetime.utcnow() - timedelta(days=7)
                        non_job_result = mongo.db.analysis_cache.delete_many({
                            "is_job_related": False,
                            "created_at": {"$lt": cutoff_date_non_job}
                        })
                        non_job_deleted = non_job_result.deleted_count
                    except Exception as e:
                        logger.error(f"Error cleaning up non-job-related cache entries: {str(e)}")
                        non_job_deleted = 0
                    
                    logger.info(f"Cache cleanup: Deleted {old_entries_deleted} old entries and {non_job_deleted} non-job-related entries")
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {str(e)}")
                
                # Sleep for 24 hours before next cleanup
                time.sleep(24 * 60 * 60)
        
        # Start the cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Cache cleanup scheduled")

    @staticmethod
    def clear_all_user_data(user):
        """
        Clear all email suggestions, applications, and cache for a user
        This is useful for testing and starting fresh
        
        Args:
            user: The user object
            
        Returns:
            dict: Counts of deleted items
        """
        try:
            user_id = str(user.id)
            
            # Clear email suggestions
            suggestions_result = mongo.db.email_suggestions.delete_many({'user_id': user_id})
            
            # Clear applications
            applications_result = mongo.db.applications.delete_many({'user_id': user_id})
            
            # Clear analysis cache
            cache_result = mongo.db.analysis_cache.delete_many({'user_id': user_id})
            
            # Reset last scan time
            user_update_result = mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$unset': {'email_settings.last_scan': ''}}
            )
            
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