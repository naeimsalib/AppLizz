"""
Yahoo Mail API Service

This service handles authentication and interaction with the Yahoo Mail API.
It provides methods for fetching and analyzing emails to identify job-related content.
"""
import os
import json
import requests
import base64
import re
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from job_app_tracker.config.yahoo_api import (
    YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, YAHOO_REDIRECT_URI,
    YAHOO_AUTH_URL, YAHOO_TOKEN_URL, YAHOO_API_BASE_URL, YAHOO_SCOPES,
    APPLICATION_KEYWORDS, INTERVIEW_KEYWORDS, REJECTION_KEYWORDS, OFFER_KEYWORDS
)
from job_app_tracker.config.mongodb import mongo
from job_app_tracker.models.user import User
from bson.objectid import ObjectId

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YahooMailService:
    @staticmethod
    def get_auth_url(user_id):
        """
        Generate the Yahoo OAuth authorization URL
        
        Args:
            user_id (str): The ID of the user to associate with this auth request
            
        Returns:
            str: The authorization URL to redirect the user to
        """
        logger.info(f"Generating Yahoo auth URL for user_id: {user_id}")
        
        if not YAHOO_CLIENT_ID:
            logger.error("Yahoo Client ID is not configured")
            raise ValueError("Yahoo Client ID is not configured")
            
        if not YAHOO_CLIENT_SECRET:
            logger.error("Yahoo Client Secret is not configured")
            raise ValueError("Yahoo Client Secret is not configured")
            
        if not YAHOO_REDIRECT_URI:
            logger.error("Yahoo Redirect URI is not configured")
            raise ValueError("Yahoo Redirect URI is not configured")
        
        # Create state parameter to include user_id for security
        state = base64.urlsafe_b64encode(user_id.encode()).decode()
        logger.info(f"Generated state parameter: {state[:10]}...")
        
        # Build authorization URL
        auth_params = {
            'client_id': YAHOO_CLIENT_ID,
            'redirect_uri': YAHOO_REDIRECT_URI,
            'response_type': 'code',
            'scope': YAHOO_SCOPES,
            'state': state
        }
        
        # Log auth parameters (excluding sensitive data)
        logger.info(f"Auth parameters:")
        logger.info(f"  client_id: {YAHOO_CLIENT_ID[:5]}...")
        logger.info(f"  redirect_uri: {YAHOO_REDIRECT_URI}")
        logger.info(f"  response_type: code")
        logger.info(f"  scope: {YAHOO_SCOPES}")
        logger.info(f"  state: {state[:10]}...")
        
        # Construct the URL with query parameters
        auth_url = f"{YAHOO_AUTH_URL}?"
        auth_url += "&".join([f"{key}={value}" for key, value in auth_params.items()])
        
        # Log the full authorization URL for debugging
        logger.info(f"Generated Yahoo auth URL: {auth_url}")
        
        return auth_url
    
    @staticmethod
    def handle_callback(code, state):
        """
        Handle the OAuth callback from Yahoo
        
        Args:
            code (str): The authorization code from Yahoo
            state (str): The state parameter containing the user_id
            
        Returns:
            tuple: (success, user_or_error_message)
        """
        try:
            logger.info(f"Handling Yahoo callback with code: {code[:5]}... and state: {state[:5]}...")
            
            # Validate parameters
            if not code:
                logger.error("Missing authorization code in callback")
                return False, "Missing authorization code"
                
            if not state:
                logger.error("Missing state parameter in callback")
                return False, "Missing state parameter"
            
            # Decode the state to get the user_id
            try:
                user_id = base64.urlsafe_b64decode(state.encode()).decode()
                logger.info(f"Decoded user_id from state: {user_id}")
            except Exception as e:
                logger.error(f"Failed to decode state parameter: {str(e)}")
                return False, f"Invalid state parameter: {str(e)}"
            
            # Exchange the code for an access token
            logger.info("Exchanging authorization code for access token")
            token_data = YahooMailService._get_token(code)
            
            if not token_data:
                logger.error("Failed to obtain access token")
                return False, "Failed to obtain access token"
            
            logger.info("Successfully obtained access token")
            
            # Get user information from Yahoo
            logger.info("Retrieving user information from Yahoo")
            user_info = YahooMailService._get_user_info(token_data['access_token'])
            
            if not user_info:
                logger.error("Failed to get user information")
                return False, "Failed to get user information"
            
            logger.info(f"Got user info: {user_info}")
            
            # Update user with Yahoo Mail credentials
            logger.info(f"Looking up user with ID: {user_id}")
            user = User.get_by_id(user_id)
            if not user:
                logger.error(f"User not found with ID: {user_id}")
                return False, "User not found"
            
            # Store the token information
            logger.info("Updating user email connection")
            user.update_email_connection(
                connected_email=user_info.get('email', 'unknown@yahoo.com'),
                provider='yahoo',
                token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token', ''),
                expiry=datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
            )
            
            logger.info(f"Successfully updated user email connection for {user_info.get('email')}")
            return True, user
            
        except Exception as e:
            logger.exception(f"Error in handle_callback: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def _get_token(code):
        """
        Exchange authorization code for access token
        
        Args:
            code (str): The authorization code from Yahoo
            
        Returns:
            dict: The token response data or None if failed
        """
        token_url = YAHOO_TOKEN_URL
        
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': YAHOO_REDIRECT_URI,
            'client_id': YAHOO_CLIENT_ID,
            'client_secret': YAHOO_CLIENT_SECRET
        }
        
        try:
            # Log detailed request information
            logger.info(f"Yahoo OAuth token request details:")
            logger.info(f"Token URL: {token_url}")
            logger.info(f"Client ID: {YAHOO_CLIENT_ID[:5]}...")  # Log partial for security
            logger.info(f"Client Secret: {YAHOO_CLIENT_SECRET[:5]}...")  # Log partial for security
            logger.info(f"Redirect URI: {YAHOO_REDIRECT_URI}")
            logger.info(f"Code: {code[:10]}...")  # Log partial for security
            
            response = requests.post(token_url, data=payload)
            
            # Log detailed response information
            logger.info(f"Yahoo OAuth token response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Token request failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {error_data}")
                except:
                    logger.error(f"Error response text: {response.text}")
                return None
                
            response.raise_for_status()
            token_data = response.json()
            logger.info("Token request successful")
            return token_data
        except Exception as e:
            logger.exception(f"Error getting token: {str(e)}")
            return None
    
    @staticmethod
    def _get_user_info(access_token):
        """
        Get user information from Yahoo
        
        Args:
            access_token (str): The access token
            
        Returns:
            dict: User information or None if failed
        """
        try:
            logger.info("Getting user information from Yahoo")
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Yahoo doesn't have a dedicated user info endpoint like Google
            # So we'll use the mail API to get the user's email
            api_url = f"{YAHOO_API_BASE_URL}/users/@me/folders"
            logger.info(f"Making request to Yahoo API: {api_url}")
            
            response = requests.get(api_url, headers=headers)
            logger.info(f"Yahoo API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"User info request failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {error_data}")
                except:
                    logger.error(f"Error response text: {response.text}")
                return None
                
            response.raise_for_status()
            
            # Extract user email from the response
            data = response.json()
            logger.info(f"Received API response data: {str(data)[:200]}...")
            
            # Try to extract email from different possible locations in the response
            user_email = None
            
            # Check if email is directly in the response
            if 'email' in data:
                user_email = data.get('email')
                logger.info(f"Found email directly in response: {user_email}")
            
            # Check if email is in the user profile
            elif 'profile' in data and 'email' in data['profile']:
                user_email = data['profile'].get('email')
                logger.info(f"Found email in profile: {user_email}")
                
            # Check if guid is available and use it to construct Yahoo email
            elif 'guid' in data:
                guid = data.get('guid')
                user_email = f"{guid}@yahoo.com"
                logger.info(f"Constructed email from guid: {user_email}")
                
            # Default fallback
            if not user_email:
                user_email = 'unknown@yahoo.com'
                logger.warning(f"Could not find email in response, using default: {user_email}")
            
            user_info = {
                'email': user_email,
                'provider': 'yahoo'
            }
            
            logger.info(f"Extracted user info: {user_info}")
            return user_info
            
        except Exception as e:
            logger.exception(f"Error getting user info: {str(e)}")
            return None
    
    @staticmethod
    def refresh_token(user):
        """
        Refresh the access token if expired
        
        Args:
            user (User): The user object
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not user.email_refresh_token:
            return False
            
        try:
            payload = {
                'grant_type': 'refresh_token',
                'refresh_token': user.email_refresh_token,
                'client_id': YAHOO_CLIENT_ID,
                'client_secret': YAHOO_CLIENT_SECRET
            }
            
            response = requests.post(YAHOO_TOKEN_URL, data=payload)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Update user with new token information
            user.update_email_connection(
                connected_email=user.connected_email,
                provider='yahoo',
                token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token', user.email_refresh_token),
                expiry=datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
            )
            
            return True
        except Exception as e:
            print(f"Error refreshing token: {str(e)}")
            return False
    
    @staticmethod
    def scan_emails(user, folder="INBOX", limit=50):
        """
        Scan Yahoo emails for job-related content
        
        Args:
            user (User): The user object
            folder (str): The folder to scan (default: INBOX)
            limit (int): Maximum number of emails to scan
            
        Returns:
            tuple: (success, message, redirect_url)
        """
        # Check if token is expired and refresh if needed
        if datetime.now() >= user.email_token_expiry:
            if not YahooMailService.refresh_token(user):
                return False, "Failed to refresh token", "main.settings"
        
        try:
            # Get emails from Yahoo Mail API
            headers = {
                'Authorization': f'Bearer {user.email_token}',
                'Accept': 'application/json'
            }
            
            # First, get the folder ID for the inbox
            response = requests.get(f"{YAHOO_API_BASE_URL}/users/@me/folders", headers=headers)
            response.raise_for_status()
            
            folders = response.json().get('folders', [])
            folder_id = None
            
            for f in folders:
                if f.get('name') == folder:
                    folder_id = f.get('id')
                    break
            
            if not folder_id:
                return False, f"Folder '{folder}' not found", "main.settings"
            
            # Get messages from the folder
            response = requests.get(
                f"{YAHOO_API_BASE_URL}/users/@me/folders/{folder_id}/messages?count={limit}",
                headers=headers
            )
            response.raise_for_status()
            
            messages = response.json().get('messages', [])
            
            # Process job-related emails
            job_applications = []
            
            for message in messages:
                message_id = message.get('id')
                
                # Get full message details
                msg_response = requests.get(
                    f"{YAHOO_API_BASE_URL}/users/@me/messages/{message_id}",
                    headers=headers
                )
                msg_response.raise_for_status()
                
                msg_data = msg_response.json()
                
                # Extract email details
                subject = msg_data.get('subject', '')
                from_email = msg_data.get('from', {}).get('email', '')
                from_name = msg_data.get('from', {}).get('name', '')
                date_str = msg_data.get('receivedDate', '')
                
                # Get email body
                body = YahooMailService._extract_email_body(msg_data)
                
                # Check if email is job-related
                if YahooMailService._is_job_related(subject, body):
                    # Extract job application information
                    company = YahooMailService._extract_company(from_email, from_name, subject, body)
                    position = YahooMailService._extract_position(subject, body)
                    status = YahooMailService._determine_status(subject, body)
                    date = YahooMailService._parse_email_date(date_str)
                    
                    job_applications.append({
                        'email_id': message_id,
                        'email_subject': subject,
                        'email_from': from_email,
                        'email_date': date,
                        'company': company,
                        'position': position,
                        'status': status,
                        'confidence': YahooMailService._calculate_confidence(subject, body, status)
                    })
            
            # Process the job applications
            if job_applications:
                suggestions_count = YahooMailService._process_applications(user, job_applications)
                return True, f"Found {len(job_applications)} potential job application emails", "main.email_suggestions"
            else:
                return True, "No job-related emails found", "main.email_suggestions"
                
        except Exception as e:
            print(f"Error scanning Yahoo emails: {str(e)}")
            return False, f"Error scanning Yahoo emails: {str(e)}", "main.email_suggestions"
    
    @staticmethod
    def _extract_email_body(msg_data):
        """
        Extract the email body from the message data
        
        Args:
            msg_data (dict): The message data from Yahoo Mail API
            
        Returns:
            str: The email body text
        """
        body = ""
        
        # Try to get HTML body first
        if 'html' in msg_data:
            html_body = msg_data.get('html', '')
            if html_body:
                # Parse HTML and extract text
                soup = BeautifulSoup(html_body, 'html.parser')
                body = soup.get_text(separator=' ', strip=True)
        
        # If no HTML body, try plain text
        if not body and 'text' in msg_data:
            body = msg_data.get('text', '')
        
        return body
    
    @staticmethod
    def _is_job_related(subject, body):
        """
        Determine if an email is job-related
        
        Args:
            subject (str): The email subject
            body (str): The email body
            
        Returns:
            bool: True if job-related, False otherwise
        """
        # Combine subject and body for analysis
        text = f"{subject} {body}".lower()
        
        # Check for job-related keywords
        for keyword in APPLICATION_KEYWORDS + INTERVIEW_KEYWORDS + REJECTION_KEYWORDS + OFFER_KEYWORDS:
            if keyword.lower() in text:
                return True
        
        return False
    
    @staticmethod
    def _extract_company(from_email, from_name, subject, body):
        """
        Extract company name from email
        
        Args:
            from_email (str): The sender's email address
            from_name (str): The sender's name
            subject (str): The email subject
            body (str): The email body
            
        Returns:
            str: The extracted company name
        """
        # Try to extract from email domain
        if from_email:
            domain = from_email.split('@')[-1]
            company_name = domain.split('.')[0]
            
            # Clean up common email domains
            if company_name not in ['gmail', 'yahoo', 'hotmail', 'outlook', 'aol', 'mail']:
                return company_name.title()
        
        # Try to extract from sender name
        if from_name and '@' not in from_name:
            # Check if sender name contains company indicators
            if any(indicator in from_name.lower() for indicator in ['hr', 'recruit', 'talent', 'career', 'job']):
                # Extract company name from sender name
                parts = from_name.split()
                if len(parts) > 1:
                    return parts[0].title()
        
        # Try to extract from subject
        company_patterns = [
            r'from\s+([A-Za-z0-9\s&]+)',
            r'at\s+([A-Za-z0-9\s&]+)',
            r'([A-Za-z0-9\s&]+)\s+team',
            r'([A-Za-z0-9\s&]+)\s+application',
            r'([A-Za-z0-9\s&]+)\s+job'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                return match.group(1).strip().title()
        
        # Default to Unknown Company
        return "Unknown Company"
    
    @staticmethod
    def _extract_position(subject, body):
        """
        Extract job position from email
        
        Args:
            subject (str): The email subject
            body (str): The email body
            
        Returns:
            str: The extracted position
        """
        # Common position patterns in subject
        position_patterns = [
            r'for\s+([A-Za-z0-9\s]+)\s+position',
            r'for\s+([A-Za-z0-9\s]+)\s+role',
            r'for\s+([A-Za-z0-9\s]+)\s+job',
            r'([A-Za-z0-9\s]+)\s+application',
            r'([A-Za-z0-9\s]+)\s+opportunity',
            r'([A-Za-z0-9\s]+)\s+role'
        ]
        
        # Try to extract from subject first
        for pattern in position_patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                position = match.group(1).strip()
                # Filter out common false positives
                if position.lower() not in ['your', 'the', 'this', 'job', 'a', 'an']:
                    return position.title()
        
        # Try to extract from body if not found in subject
        for pattern in position_patterns:
            match = re.search(pattern, body[:500], re.IGNORECASE)  # Only search beginning of body
            if match:
                position = match.group(1).strip()
                # Filter out common false positives
                if position.lower() not in ['your', 'the', 'this', 'job', 'a', 'an']:
                    return position.title()
        
        # Default to Unknown Position
        return "Unknown Position"
    
    @staticmethod
    def _determine_status(subject, body):
        """
        Determine the application status from email content
        
        Args:
            subject (str): The email subject
            body (str): The email body
            
        Returns:
            str: The determined status
        """
        text = f"{subject} {body}".lower()
        
        # Check for rejection indicators
        for keyword in REJECTION_KEYWORDS:
            if keyword.lower() in text:
                return "Rejected"
        
        # Check for interview indicators
        for keyword in INTERVIEW_KEYWORDS:
            if keyword.lower() in text:
                return "Interview"
        
        # Check for offer indicators
        for keyword in OFFER_KEYWORDS:
            if keyword.lower() in text:
                return "Offer"
        
        # Default to Applied for new applications
        return "Applied"
    
    @staticmethod
    def _parse_email_date(date_str):
        """
        Parse email date string to datetime
        
        Args:
            date_str (str): The date string from email
            
        Returns:
            datetime: The parsed date
        """
        try:
            # Yahoo Mail API returns timestamp in milliseconds
            if date_str.isdigit():
                timestamp = int(date_str) / 1000  # Convert to seconds
                return datetime.fromtimestamp(timestamp)
            
            # Try various date formats
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%d %b %Y %H:%M:%S %z']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Default to current date if parsing fails
            return datetime.now()
        except Exception:
            return datetime.now()
    
    @staticmethod
    def _calculate_confidence(subject, body, status):
        """
        Calculate confidence score for the classification
        
        Args:
            subject (str): The email subject
            body (str): The email body
            status (str): The determined status
            
        Returns:
            float: Confidence score (0-1)
        """
        text = f"{subject} {body}".lower()
        
        # Count keyword matches based on status
        keyword_count = 0
        total_keywords = 0
        
        if status == "Applied":
            keywords = APPLICATION_KEYWORDS
        elif status == "Interview":
            keywords = INTERVIEW_KEYWORDS
        elif status == "Rejected":
            keywords = REJECTION_KEYWORDS
        elif status == "Offer":
            keywords = OFFER_KEYWORDS
        else:
            return 0.5  # Default confidence
        
        for keyword in keywords:
            total_keywords += 1
            if keyword.lower() in text:
                keyword_count += 1
        
        # Calculate confidence score
        if total_keywords > 0:
            return min(0.5 + (keyword_count / total_keywords * 0.5), 1.0)
        else:
            return 0.5
    
    @staticmethod
    def _process_applications(user, job_applications):
        """
        Process job applications found in emails
        Creates suggestions for the user to review
        
        Args:
            user (User): The user object
            job_applications (list): List of job applications
            
        Returns:
            int: Number of suggestions created
        """
        # Get existing applications for the user
        existing_applications = list(mongo.db.applications.find({'user_id': str(user.id)}))
        
        # Create suggestions
        suggestions = {
            'user_id': str(user.id),
            'processed': False,
            'created_at': datetime.now(),
            'suggestions': []
        }
        
        for job_app in job_applications:
            # Check if this application already exists
            existing_app = None
            for app in existing_applications:
                if (app.get('company', '').lower() == job_app['company'].lower() and
                    app.get('position', '').lower() == job_app['position'].lower()):
                    existing_app = app
                    break
            
            if existing_app:
                # Check if status has changed
                if existing_app.get('status') != job_app['status']:
                    suggestions['suggestions'].append({
                        'type': 'update',
                        'application_id': str(existing_app['_id']),
                        'company': job_app['company'],
                        'position': job_app['position'],
                        'current_status': existing_app.get('status', 'Applied'),
                        'new_status': job_app['status'],
                        'email_subject': job_app.get('email_subject', 'No Subject'),
                        'date': job_app.get('email_date', datetime.now())
                    })
            else:
                # New application
                suggestions['suggestions'].append({
                    'type': 'new',
                    'company': job_app['company'],
                    'position': job_app['position'],
                    'status': job_app['status'],
                    'email_subject': job_app.get('email_subject', 'No Subject'),
                    'date': job_app.get('email_date', datetime.now())
                })
        
        # Save suggestions to database
        if suggestions['suggestions']:
            mongo.db.email_suggestions.insert_one(suggestions)
            return len(suggestions['suggestions'])
        
        return 0 