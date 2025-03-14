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

# NLTK resources will be downloaded on-demand when needed
nltk_resources_downloaded = False

# Constants
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
OUTLOOK_SCOPES = ['offline_access', 'Mail.Read']
YAHOO_IMAP_SERVER = 'imap.mail.yahoo.com'
YAHOO_IMAP_PORT = 993

# Keywords for job application detection
APPLICATION_KEYWORDS = [
    'application', 'job', 'position', 'resume', 'cv', 'candidate', 'opportunity',
    'interview', 'hiring', 'recruitment', 'talent', 'career', 'employment'
]

# Keywords for status detection
STATUS_KEYWORDS = {
    'applied': ['received', 'submitted', 'confirm', 'application', 'received', 'thank you for applying'],
    'in_progress': ['reviewing', 'under review', 'being considered', 'in consideration', 'processing'],
    'interview': ['interview', 'meet', 'discuss', 'conversation', 'schedule', 'availability'],
    'rejected': ['unfortunately', 'not selected', 'other candidates', 'not moving forward', 'not proceeding', 'regret'],
    'offer': ['offer', 'congratulations', 'pleased to inform', 'welcome', 'join our team', 'compensation']
}

class EmailService:
    @staticmethod
    def _ensure_nltk_resources():
        """Ensure NLTK resources are downloaded when needed"""
        global nltk_resources_downloaded
        if not nltk_resources_downloaded:
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
            
            nltk_resources_downloaded = True

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
                # Hash the app password before storing
                hashed_password = generate_password_hash(app_password)
                
                # Set expiry to 1 year from now (app passwords don't expire)
                expiry = datetime.utcnow() + timedelta(days=365)
                
                user.update_email_connection(
                    connected_email=yahoo_email,
                    provider='yahoo_imap',
                    token=hashed_password,  # Store hashed password as token
                    refresh_token=None,     # No refresh token for IMAP
                    expiry=expiry
                )
                
                # Close the connection
                mail.logout()
                
                return True, user
            
            return False, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def scan_emails(user):
        """Scan emails for job applications"""
        if not user.email_connected:
            return False, "Email not connected"
        
        if user.email_provider == 'gmail':
            return EmailService._scan_gmail(user)
        elif user.email_provider == 'yahoo_imap':
            return EmailService._scan_yahoo_imap(user)
        elif user.email_provider == 'outlook':
            return EmailService._scan_outlook(user)
        
        return False, "Unsupported email provider"
    
    @staticmethod
    def _scan_gmail(user):
        """Scan Gmail for job applications"""
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
        if user.email_token_expiry < datetime.utcnow():
            credentials.refresh(requests.Request())
            # Update tokens in database
            user.update_email_connection(
                connected_email=user.connected_email,
                provider='gmail',
                token=credentials.token,
                refresh_token=credentials.refresh_token,
                expiry=datetime.utcnow() + timedelta(seconds=credentials.expiry)
            )
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Get last scan time
        last_scan = user.email_settings.get('last_scan')
        query = "newer_than:30d"  # Default to last 30 days
        if last_scan:
            # Convert to days ago for Gmail query
            days_ago = (datetime.utcnow() - last_scan).days + 1
            query = f"newer_than:{days_ago}d"
        
        # Search for job-related emails
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        job_applications = []
        
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            
            # Extract email data
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract email body
            body = EmailService._get_email_body(msg['payload'])
            
            # Check if this is a job-related email
            if EmailService._is_job_related(subject, body):
                # Extract company name
                company = EmailService._extract_company(from_email, subject, body)
                
                # Extract position
                position = EmailService._extract_position(subject, body)
                
                # Determine status
                status = EmailService._determine_status(subject, body)
                
                if company and status:
                    job_applications.append({
                        'company': company,
                        'position': position,
                        'status': status,
                        'email_id': message['id'],
                        'subject': subject,
                        'date': EmailService._parse_email_date(date_str)
                    })
        
        # Update last scan time
        settings = user.email_settings
        settings['last_scan'] = datetime.utcnow()
        user.update_email_settings(settings)
        
        # Process found applications
        if job_applications:
            EmailService._process_applications(user, job_applications)
            
        return True, f"Found {len(job_applications)} job-related emails"
    
    @staticmethod
    def _scan_yahoo_imap(user):
        """Scan Yahoo Mail using IMAP"""
        try:
            # Create an SSL context with certificate verification
            context = ssl.create_default_context()
            
            # Connect to Yahoo Mail's IMAP server
            mail = imaplib.IMAP4_SSL(YAHOO_IMAP_SERVER, YAHOO_IMAP_PORT, ssl_context=context)
            
            # Check password from token (unhashed)
            # In a real implementation, you would need a secure way to store and retrieve the app password
            # This is a simplified example
            app_password = user.email_token  # In reality, this should be securely stored and retrieved
            
            # Login using the user's Yahoo credentials
            mail.login(user.connected_email, app_password)
            
            # Select the inbox
            mail.select("INBOX")
            
            # Get last scan time
            last_scan = user.email_settings.get('last_scan')
            search_criteria = "ALL"
            
            if last_scan:
                # Format date for IMAP search
                date_str = last_scan.strftime("%d-%b-%Y")
                search_criteria = f'(SINCE "{date_str}")'
            
            # Search for emails matching criteria
            status, messages = mail.search(None, search_criteria)
            
            job_applications = []
            
            # Process each email
            for num in messages[0].split():
                status, msg_data = mail.fetch(num, '(RFC822)')
                raw_email = msg_data[0][1]
                
                # Parse the raw email
                msg = email.message_from_bytes(raw_email)
                
                # Extract email data
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                    
                from_email = msg.get("From", "")
                date_str = msg.get("Date", "")
                
                # Extract email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        if "attachment" not in content_disposition:
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                            elif content_type == "text/html" and not body:
                                html = part.get_payload(decode=True).decode()
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html, 'html.parser')
                                body = soup.get_text()
                else:
                    body = msg.get_payload(decode=True).decode()
                
                # Check if this is a job-related email
                if EmailService._is_job_related(subject, body):
                    # Extract company name
                    company = EmailService._extract_company(from_email, subject, body)
                    
                    # Extract position
                    position = EmailService._extract_position(subject, body)
                    
                    # Determine status
                    status = EmailService._determine_status(subject, body)
                    
                    if company and status:
                        job_applications.append({
                            'company': company,
                            'position': position,
                            'status': status,
                            'email_id': num.decode(),
                            'subject': subject,
                            'date': EmailService._parse_email_date(date_str)
                        })
            
            # Logout
            mail.logout()
            
            # Update last scan time
            settings = user.email_settings
            settings['last_scan'] = datetime.utcnow()
            user.update_email_settings(settings)
            
            # Process found applications
            if job_applications:
                EmailService._process_applications(user, job_applications)
                
            return True, f"Found {len(job_applications)} job-related emails"
            
        except Exception as e:
            return False, f"Error scanning Yahoo Mail: {str(e)}"
    
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
        """Check if an email is job-related based on its subject and body"""
        EmailService._ensure_nltk_resources()
        combined_text = (subject + " " + body).lower()
        
        # Check for job-related keywords
        keyword_count = sum(1 for keyword in APPLICATION_KEYWORDS if keyword.lower() in combined_text)
        
        # If multiple keywords found, likely job-related
        return keyword_count >= 2
    
    @staticmethod
    def _extract_company(from_email, subject, body):
        """Extract company name from email"""
        EmailService._ensure_nltk_resources()
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
        """Extract job position from email"""
        EmailService._ensure_nltk_resources()
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
        """Determine application status from email content"""
        EmailService._ensure_nltk_resources()
        combined_text = (subject + " " + body).lower()
        
        # Check for each status type
        status_scores = {}
        
        for status, keywords in STATUS_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword.lower() in combined_text)
            status_scores[status] = score
        
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
    def _process_applications(user, job_applications):
        """Process found job applications"""
        # Get existing applications
        existing_apps = list(mongo.db.applications.find({'user_id': str(user.id)}))
        
        # Track suggested changes
        suggested_changes = []
        
        for job_app in job_applications:
            # Check if company exists in user's applications
            company_match = next((app for app in existing_apps if 
                                 app['company'].lower() == job_app['company'].lower() or
                                 job_app['company'].lower() in app['company'].lower() or
                                 app['company'].lower() in job_app['company'].lower()), None)
            
            if company_match:
                # Check if status should be updated
                current_status = company_match.get('status')
                new_status = job_app['status']
                
                # Status priority (higher number = higher priority)
                status_priority = {
                    'Applied': 1,
                    'In Progress': 2,
                    'Interview': 3,
                    'Offer': 4,
                    'Rejected': 5
                }
                
                # Only update if new status has higher priority
                if status_priority.get(new_status, 0) > status_priority.get(current_status, 0):
                    if user.email_settings.get('require_approval', True):
                        # Add to suggested changes
                        suggested_changes.append({
                            'type': 'update',
                            'application_id': str(company_match['_id']),
                            'company': company_match['company'],
                            'position': company_match['position'],
                            'current_status': current_status,
                            'new_status': new_status,
                            'email_subject': job_app['subject'],
                            'date': job_app['date']
                        })
                    else:
                        # Update directly
                        mongo.db.applications.update_one(
                            {'_id': company_match['_id']},
                            {'$set': {'status': new_status}}
                        )
            else:
                # New application
                if user.email_settings.get('require_approval', True):
                    # Add to suggested changes
                    suggested_changes.append({
                        'type': 'new',
                        'company': job_app['company'],
                        'position': job_app['position'],
                        'status': job_app['status'],
                        'email_subject': job_app['subject'],
                        'date': job_app['date']
                    })
                else:
                    # Add directly
                    new_app = {
                        'user_id': str(user.id),
                        'company': job_app['company'],
                        'position': job_app['position'] if job_app['position'] != 'Unknown Position' else '',
                        'status': job_app['status'],
                        'date_applied': job_app['date'],
                        'notes': f"Automatically added from email: {job_app['subject']}",
                        'created_at': datetime.utcnow()
                    }
                    mongo.db.applications.insert_one(new_app)
        
        # Store suggested changes if any
        if suggested_changes:
            mongo.db.email_suggestions.insert_one({
                'user_id': str(user.id),
                'suggestions': suggested_changes,
                'created_at': datetime.utcnow(),
                'processed': False
            })
        
        return len(suggested_changes) 