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
import html2text
from flask import current_app
import threading
import csv
from pathlib import Path
from job_app_tracker.config.logging import logger

# Create logs directory if it doesn't exist
Path('logs').mkdir(parents=True, exist_ok=True)
Path('logs/analysis').mkdir(parents=True, exist_ok=True)

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

# Enhanced keywords for job application detection
APPLICATION_KEYWORDS = {
    'strong_indicators': [
        'thank you for applying', 'application has been received', 'application received',
        'application submitted', 'thank you for your application', 'we have received your application',
        'submission received', 'thank you for your interest', 'application complete',
        'successfully applied', 'application has been submitted', 'interview invitation',
        'schedule an interview', 'interview request', 'interview confirmation',
        'interview schedule', 'interview details', 'interview with', 'invite you to interview',
        'interview process', 'job offer', 'offer letter', 'pleased to offer', 'formal offer',
        'compensation', 'salary', 'benefits', 'start date', 'onboarding', 'welcome to the team',
        'join our team', 'employment offer'
    ],
    'general_indicators': [
        'application', 'job', 'position', 'resume', 'cv', 'candidate', 'opportunity',
        'interview', 'hiring', 'recruitment', 'talent', 'career', 'employment',
        'role', 'job posting', 'career opportunity', 'job description', 'job requisition',
        'job title', 'job opening', 'job vacancy', 'job id', 'req id', 'requisition'
    ],
    'status_indicators': {
        'applied': [
            'thank you for applying', 'application has been received', 'application received',
            'application submitted', 'thank you for your application', 'we have received your application',
            'submission received', 'thank you for your interest', 'application complete',
            'successfully applied', 'application has been submitted'
        ],
        'in_progress': [
            'reviewing', 'under review', 'being considered', 'in consideration', 'processing',
            'application is being reviewed', 'currently reviewing', 'assessment', 'evaluation',
            'screening', 'pre-screening', 'application process', 'next steps', 'under consideration',
            'being reviewed', 'initial review', 'preliminary review', 'application is in progress',
            'moving forward with your application', 'coding challenge', 'technical assessment',
            'skills assessment', 'online assessment', 'take-home assignment', 'questionnaire',
            'additional information needed'
        ],
        'interview': [
            'schedule an interview', 'interview invitation', 'interview request',
            'interview confirmation', 'interview schedule', 'interview details',
            'interview with', 'invite you to interview', 'interview process',
            'phone interview', 'video interview', 'in-person interview', 'meeting',
            'confirm interview', 'interview invitation', 'would like to speak with you',
            'interview process', 'schedule a time', 'virtual interview', 'zoom interview',
            'teams meeting', 'google meet', 'phone screen', 'technical interview',
            'hiring manager', 'panel interview', 'second interview', 'final interview',
            'follow-up interview', 'interview with the team', 'meet the team'
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
            'job offer', 'offer letter', 'pleased to offer', 'formal offer',
            'compensation', 'salary', 'benefits', 'start date', 'onboarding',
            'welcome to the team', 'join our team', 'employment offer',
            'we are delighted', 'we are pleased', 'we would like to offer',
            'offer of employment', 'employment offer', 'offer details',
            'accept the offer', 'offer acceptance', 'employment contract',
            'starting salary', 'compensation package', 'benefits package',
            'contingent offer', 'conditional offer', 'official offer'
        ]
    }
}

# Company name patterns
COMPANY_PATTERNS = [
    r'(?:from|at|with)\s+([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Corp|Corporation|Company))',
    r'([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Corp|Corporation|Company))',
    r'(?:team|recruiting|talent|hr)(?:\s+at)?\s+([A-Z][A-Za-z0-9\s&]+)',
    r'(?:best regards|regards|sincerely|thanks),?\s*([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Corp|Corporation|Company))',
    r'([A-Z][A-Za-z0-9\s&]+(?:Inc|LLC|Ltd|Corp|Corporation|Company))\s*$'
]

# Position patterns
POSITION_PATTERNS = [
    r'(?:position|role|job|opportunity)(?:\s+for)?\s+(?:of\s+)?([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))',
    r'([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))\s+(?:position|role|job|opportunity)',
    r'(?:applying|application|candidacy)\s+for\s+([A-Za-z0-9\s]+)',
    r'(?:looking for|seeking|hiring)\s+([A-Za-z0-9\s]+)',
    r'([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))(?:\s+at|\s+with|\s+for)?\s+[A-Za-z0-9\s]+',
    r'[A-Za-z0-9\s]+(?:\s+at|\s+with|\s+for)?\s+([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))'
]

class EmailService:
    _cache = {}
    _cache_ttl = 3600  # 1 hour in seconds
    _email_cache = {}  # Cache for processed emails
    _email_cache_ttl = 7 * 24 * 3600  # 7 days in seconds
    _analysis_cache = {}  # Cache for email analysis results

    @staticmethod
    def _init_cache():
        """Initialize the cache collections in MongoDB"""
        try:
            # Create TTL index for analysis cache
            mongo.db.analysis_cache.create_index(
                "created_at",
                expireAfterSeconds=EmailService._cache_ttl
            )
            logger.info("TTL index created successfully")
        except Exception as e:
            logger.error(f"Error creating TTL index: {str(e)}")

    @staticmethod
    def _get_cached_email(email_id, user_id):
        """Get cached email analysis result"""
        try:
            cache_key = f"{user_id}_{email_id}"
            cached_data = EmailService._analysis_cache.get(cache_key)
            if cached_data:
                return cached_data
            return None
        except Exception as e:
            logger.error(f"Error getting cached email: {str(e)}")
            return None

    @staticmethod
    def _cache_email(email_id, user_id, analysis_data):
        """Cache email analysis result"""
        try:
            cache_key = f"{user_id}_{email_id}"
            EmailService._analysis_cache[cache_key] = analysis_data
        except Exception as e:
            logger.error(f"Error caching email: {str(e)}")

    @staticmethod
    def _clear_cache():
        """Clear all caches"""
        try:
            EmailService._cache.clear()
            EmailService._email_cache.clear()
            EmailService._analysis_cache.clear()
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")

    @staticmethod
    def _cleanup_expired_cache():
        """Clean up expired cache entries"""
        try:
            current_time = time.time()
            # Clean up email cache
            EmailService._email_cache = {
                k: v for k, v in EmailService._email_cache.items()
                if current_time - v.get('timestamp', 0) < EmailService._email_cache_ttl
            }
            # Clean up analysis cache
            EmailService._analysis_cache = {
                k: v for k, v in EmailService._analysis_cache.items()
                if current_time - v.get('timestamp', 0) < EmailService._cache_ttl
            }
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}")

    @staticmethod
    def _create_analysis_log(user_id, scan_id):
        """Create a new analysis log file for a scan session"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'job_app_tracker/logs/analysis/scan_{user_id}_{timestamp}_{scan_id}.csv'
        
        # Create CSV file with headers
        with open(log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Email ID', 'Subject', 'From', 'Date', 'Is Job Related',
                'Company', 'Position', 'Status', 'Job URL', 'Deadline',
                'Notes', 'Confidence', 'Analysis Method', 'Matched Keywords',
                'Analysis Time'
            ])
        
        return log_file

    @staticmethod
    def _log_email_analysis(log_file, analysis_data):
        """Log email analysis results to CSV file"""
        try:
            with open(log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    analysis_data.get('email_id', ''),
                    analysis_data.get('subject', ''),
                    analysis_data.get('from_email', ''),
                    analysis_data.get('date', ''),
                    analysis_data.get('is_job_related', False),
                    analysis_data.get('company', ''),
                    analysis_data.get('position', ''),
                    analysis_data.get('status', ''),
                    analysis_data.get('job_url', ''),
                    analysis_data.get('deadline', ''),
                    analysis_data.get('notes', ''),
                    analysis_data.get('confidence', 0),
                    analysis_data.get('analysis_method', ''),
                    ','.join(analysis_data.get('matched_keywords', [])),
                    datetime.now().isoformat()
                ])
        except Exception as e:
            logger.error(f"Error logging email analysis: {str(e)}")

    @staticmethod
    def _analyze_email_content(subject, body, from_email):
        """
        Enhanced email content analysis with strict validation
        Returns detailed analysis results with confidence scores
        """
        start_time = time.time()
        analysis_result = {
            'is_job_related': False,
            'company': 'Unknown Company',
            'position': 'Unknown Position',
            'status': 'Applied',
            'job_url': '',
            'deadline': None,
            'notes': '',
            'confidence': 0.0,
            'analysis_method': 'traditional',
            'matched_keywords': [],
            'analysis_time': 0,
            'validation_checks': []
        }

        # Combine text for analysis
        combined_text = (subject + " " + body).lower()
        
        # Validation checks
        validation_checks = []
        
        # 1. Check if it's a marketing email
        marketing_indicators = [
            'unsubscribe', 'marketing', 'newsletter', 'promotion', 'special offer',
            'limited time', 'exclusive offer', 'deal', 'discount', 'sale',
            'sponsored', 'advertisement', 'advert', 'promotional'
        ]
        
        if any(indicator in combined_text for indicator in marketing_indicators):
            validation_checks.append('Marketing email detected')
            analysis_result['is_job_related'] = False
            analysis_result['confidence'] = 0.0
            analysis_result['notes'] = 'Marketing email detected'
            analysis_result['validation_checks'] = validation_checks
            analysis_result['analysis_time'] = time.time() - start_time
            return analysis_result
        
        # 2. Check for strong job-related indicators
        strong_matches = []
        for indicator in APPLICATION_KEYWORDS['strong_indicators']:
            if indicator.lower() in combined_text:
                strong_matches.append(indicator)
                analysis_result['matched_keywords'].append(indicator)
        
        if strong_matches:
            validation_checks.append(f'Strong job indicators found: {", ".join(strong_matches)}')
            analysis_result['is_job_related'] = True
            analysis_result['confidence'] = 0.9
        else:
            validation_checks.append('No strong job indicators found')
        
        # 3. Check for general indicators only if no strong indicators
        if not analysis_result['is_job_related']:
            general_matches = []
            for indicator in APPLICATION_KEYWORDS['general_indicators']:
                if indicator.lower() in combined_text:
                    general_matches.append(indicator)
                    analysis_result['matched_keywords'].append(indicator)
            
            if general_matches:
                validation_checks.append(f'General job indicators found: {", ".join(general_matches)}')
                # Require at least 2 general indicators for job-related classification
                if len(general_matches) >= 2:
                    analysis_result['is_job_related'] = True
                    analysis_result['confidence'] = 0.7
                else:
                    validation_checks.append('Insufficient general indicators')
            else:
                validation_checks.append('No general job indicators found')
        
        # 4. Extract and validate company name
        company_matches = []
        for pattern in COMPANY_PATTERNS:
            matches = re.findall(pattern, combined_text)
            company_matches.extend(matches)
        
        if company_matches:
            # Clean and validate company names
            valid_companies = []
            for company in company_matches:
                company = company.strip()
                if len(company) > 2 and not company.lower() in ['inc', 'llc', 'ltd', 'corp']:
                    valid_companies.append(company)
            
            if valid_companies:
                analysis_result['company'] = valid_companies[0]
                validation_checks.append(f'Company identified: {valid_companies[0]}')
            else:
                validation_checks.append('No valid company names found')
        else:
            validation_checks.append('No company names found')
        
        # 5. Extract and validate position
        position_matches = []
        for pattern in POSITION_PATTERNS:
            matches = re.findall(pattern, combined_text)
            position_matches.extend(matches)
        
        if position_matches:
            # Clean and validate position names
            valid_positions = []
            for position in position_matches:
                position = position.strip()
                if len(position) > 2:
                    valid_positions.append(position)
            
            if valid_positions:
                analysis_result['position'] = valid_positions[0]
                validation_checks.append(f'Position identified: {valid_positions[0]}')
            else:
                validation_checks.append('No valid position titles found')
        else:
            validation_checks.append('No position titles found')
        
        # 6. Determine application status
        status_scores = {
            'applied': 0,
            'in_progress': 0,
            'interview': 0,
            'rejected': 0,
            'offer': 0
        }
        
        for status, keywords in APPLICATION_KEYWORDS['status_indicators'].items():
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    status_scores[status] += 1
        
        # Get the status with the highest score
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
    def _scan_yahoo_imap(user):
        """
        Scan Yahoo Mail for job application emails with enhanced logging and validation
        """
        scan_id = str(int(time.time()))
        log_file = EmailService._create_analysis_log(user.id, scan_id)
        
        try:
            # Connect to Yahoo IMAP with retry logic
            max_retries = 3
            retry_count = 0
            imap = None
            
            while retry_count < max_retries:
                try:
                    # Create an SSL context with certificate verification and modern protocols
                    context = ssl.create_default_context()
                    context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3  # Disable older protocols
                    context.minimum_version = ssl.TLSVersion.TLSv1_2  # Require TLS 1.2 or higher
                    
                    imap = imaplib.IMAP4_SSL('imap.mail.yahoo.com', ssl_context=context)
                    imap.login(user.connected_email, user.email_password)
                    imap.select('INBOX')
                    break
                except (ssl.SSLError, imaplib.IMAP4.error) as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise Exception(f"Failed to connect to Yahoo Mail after {max_retries} attempts: {str(e)}")
                    time.sleep(1)  # Wait before retrying
            
            # Get the last 100 emails
            _, message_numbers = imap.search(None, 'ALL')
            email_ids = message_numbers[0].split()
            total_emails = len(email_ids)
            
            # Process the last 100 emails
            emails_to_process = email_ids[-100:] if total_emails > 100 else email_ids
            logger.info(f"Processing {len(emails_to_process)} emails out of {total_emails} total emails")
            
            job_applications = []
            processed_count = 0
            marketing_emails = 0
            job_related_emails = 0
            
            for email_id in reversed(emails_to_process):
                try:
                    # Check if email is already processed
                    cached_data = EmailService._get_cached_email(email_id, user.id)
                    if cached_data:
                        processed_count += 1
                        if cached_data.get('is_job_related'):
                            job_applications.append(cached_data)
                            job_related_emails += 1
                        EmailService._log_email_analysis(log_file, cached_data)
                        continue
                    
                    # Fetch email
                    _, msg_data = imap.fetch(email_id, '(RFC822)')
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Extract email details
                    subject = email_message.get('subject', '')
                    from_email = email_message.get('from', '')
                    date_str = email_message.get('date', '')
                    
                    # Decode headers properly
                    if isinstance(subject, str):
                        subject = subject
                    else:
                        subject = str(subject)
                    
                    if isinstance(from_email, str):
                        from_email = from_email
                    else:
                        from_email = str(from_email)
                    
                    # Get email body
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                except:
                                    body = part.get_payload(decode=True).decode('latin1', errors='replace')
                    else:
                        try:
                            body = email_message.get_payload(decode=True).decode('utf-8', errors='replace')
                        except:
                            body = email_message.get_payload(decode=True).decode('latin1', errors='replace')
                    
                    # Analyze email content
                    analysis_result = EmailService._analyze_email_content(subject, body, from_email)
                    
                    # Add email metadata to analysis result
                    analysis_result.update({
                        'email_id': email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                        'subject': subject,
                        'from_email': from_email,
                        'date': EmailService._parse_email_date(date_str)
                    })
                    
                    # Log analysis result
                    EmailService._log_email_analysis(log_file, analysis_result)
                    
                    # Update counters
                    if not analysis_result['is_job_related'] and any('Marketing email detected' in check for check in analysis_result.get('validation_checks', [])):
                        marketing_emails += 1
                    elif analysis_result['is_job_related']:
                        job_related_emails += 1
                        job_applications.append(analysis_result)
                        EmailService._cache_email(email_id, user.id, analysis_result)
                    
                    processed_count += 1
                    
                    # Log progress
                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count}/{len(emails_to_process)} emails. "
                                  f"Found {job_related_emails} job-related emails and {marketing_emails} marketing emails.")
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {str(e)}")
                    continue
            
            # Log final results
            logger.info(f"Email scan completed:")
            logger.info(f"- Total emails processed: {processed_count}")
            logger.info(f"- Job-related emails: {job_related_emails}")
            logger.info(f"- Marketing emails: {marketing_emails}")
            logger.info(f"- Other emails: {processed_count - job_related_emails - marketing_emails}")
            
            imap.close()
            imap.logout()
            
            return {
                'success': True,
                'processed_count': processed_count,
                'total_count': len(emails_to_process),
                'job_applications': job_applications,
                'log_file': log_file,
                'stats': {
                    'job_related': job_related_emails,
                    'marketing': marketing_emails,
                    'other': processed_count - job_related_emails - marketing_emails
                }
            }
            
        except Exception as e:
            logger.error(f"Error in Yahoo IMAP scan: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_count': processed_count,
                'total_count': len(emails_to_process) if 'emails_to_process' in locals() else 0,
                'job_applications': job_applications,
                'log_file': log_file
            }

    @staticmethod
    def _scan_gmail(user):
        """
        Scan Gmail for job application emails with enhanced logging
        """
        scan_id = str(int(time.time()))
        log_file = EmailService._create_analysis_log(user.id, scan_id)
        
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
            processed_count = 0
            
            # Process each message
            for message in messages:
                try:
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
                    
                    # Analyze email content
                    analysis_result = EmailService._analyze_email_content(subject, body, from_email)
                    
                    # Add email metadata to analysis result
                    analysis_result.update({
                        'email_id': message['id'],
                        'subject': subject,
                        'from_email': from_email,
                        'date': email_date
                    })
                    
                    # Log analysis result
                    EmailService._log_email_analysis(log_file, analysis_result)
                    
                    # If job-related, add to list
                    if analysis_result['is_job_related']:
                        job_applications.append(analysis_result)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing Gmail message {message['id']}: {str(e)}")
                    continue
            
            return {
                'success': True,
                'processed_count': processed_count,
                'total_count': len(messages),
                'job_applications': job_applications,
                'log_file': log_file
            }
            
        except Exception as e:
            logger.error(f"Error scanning Gmail for user {user.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_count': 0,
                'total_count': 0,
                'job_applications': [],
                'log_file': log_file
            }

    @staticmethod
    def _review_scan_results(log_file):
        """
        Review the scan results and analyze accuracy
        """
        try:
            with open(log_file, 'r') as f:
                reader = csv.DictReader(f)
                results = list(reader)
            
            total_emails = len(results)
            job_related = sum(1 for r in results if r['Is Job Related'].lower() == 'true')
            high_confidence = sum(1 for r in results if float(r['Confidence']) >= 0.8)
            
            # Calculate accuracy metrics
            metrics = {
                'total_emails': total_emails,
                'job_related_count': job_related,
                'high_confidence_count': high_confidence,
                'job_related_percentage': (job_related / total_emails * 100) if total_emails > 0 else 0,
                'high_confidence_percentage': (high_confidence / total_emails * 100) if total_emails > 0 else 0
            }
            
            # Log review results
            logger.info(f"Scan Results Review for {log_file}:")
            logger.info(f"Total emails processed: {metrics['total_emails']}")
            logger.info(f"Job-related emails: {metrics['job_related_count']} ({metrics['job_related_percentage']:.1f}%)")
            logger.info(f"High confidence results: {metrics['high_confidence_count']} ({metrics['high_confidence_percentage']:.1f}%)")
            
            # Analyze patterns and keywords
            if total_emails > 0:
                # Collect all matched keywords
                all_keywords = []
                for result in results:
                    keywords = result['Matched Keywords'].split(',')
                    all_keywords.extend([k.strip() for k in keywords if k.strip()])
                
                # Count keyword frequencies
                keyword_freq = {}
                for keyword in all_keywords:
                    keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
                
                # Sort keywords by frequency
                sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
                
                # Log keyword analysis
                logger.info("\nKeyword Analysis:")
                for keyword, freq in sorted_keywords[:20]:  # Top 20 keywords
                    percentage = (freq / total_emails) * 100
                    logger.info(f"{keyword}: {freq} occurrences ({percentage:.1f}%)")
                
                # Analyze false positives and negatives
                false_positives = []
                false_negatives = []
                
                for result in results:
                    if result['Is Job Related'].lower() == 'true' and float(result['Confidence']) < 0.5:
                        false_positives.append({
                            'subject': result['Subject'],
                            'from': result['From'],
                            'confidence': result['Confidence']
                        })
                    elif result['Is Job Related'].lower() == 'false' and float(result['Confidence']) > 0.7:
                        false_negatives.append({
                            'subject': result['Subject'],
                            'from': result['From'],
                            'confidence': result['Confidence']
                        })
                
                if false_positives:
                    logger.info("\nPotential False Positives:")
                    for fp in false_positives[:5]:  # Top 5 false positives
                        logger.info(f"Subject: {fp['subject']}")
                        logger.info(f"From: {fp['from']}")
                        logger.info(f"Confidence: {fp['confidence']}")
                
                if false_negatives:
                    logger.info("\nPotential False Negatives:")
                    for fn in false_negatives[:5]:  # Top 5 false negatives
                        logger.info(f"Subject: {fn['subject']}")
                        logger.info(f"From: {fn['from']}")
                        logger.info(f"Confidence: {fn['confidence']}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error reviewing scan results: {str(e)}")
            return None

    @staticmethod
    def analyze_log_files():
        """
        Analyze all log files in the analysis directory to identify patterns
        and suggest improvements to the analysis system.
        """
        try:
            analysis_dir = Path('job_app_tracker/logs/analysis')
            if not analysis_dir.exists():
                logger.warning("Analysis directory not found")
                return
            
            # Get all CSV files
            log_files = list(analysis_dir.glob('*.csv'))
            if not log_files:
                logger.warning("No log files found")
                return
            
            # Collect data from all files
            all_results = []
            for log_file in log_files:
                try:
                    with open(log_file, 'r') as f:
                        reader = csv.DictReader(f)
                        all_results.extend(list(reader))
                except Exception as e:
                    logger.error(f"Error reading log file {log_file}: {str(e)}")
                    continue
            
            if not all_results:
                logger.warning("No results found in log files")
                return
            
            # Analyze patterns
            total_emails = len(all_results)
            job_related = sum(1 for r in all_results if r['Is Job Related'].lower() == 'true')
            high_confidence = sum(1 for r in all_results if float(r['Confidence']) >= 0.8)
            
            # Calculate overall metrics
            metrics = {
                'total_emails': total_emails,
                'job_related_count': job_related,
                'high_confidence_count': high_confidence,
                'job_related_percentage': (job_related / total_emails * 100) if total_emails > 0 else 0,
                'high_confidence_percentage': (high_confidence / total_emails * 100) if total_emails > 0 else 0
            }
            
            # Log overall analysis
            logger.info("\nOverall Analysis Results:")
            logger.info(f"Total emails analyzed: {metrics['total_emails']}")
            logger.info(f"Job-related emails: {metrics['job_related_count']} ({metrics['job_related_percentage']:.1f}%)")
            logger.info(f"High confidence results: {metrics['high_confidence_count']} ({metrics['high_confidence_percentage']:.1f}%)")
            
            # Analyze company patterns
            company_patterns = {}
            for result in all_results:
                company = result['Company']
                if company and company != 'Unknown Company':
                    company_patterns[company] = company_patterns.get(company, 0) + 1
            
            # Log company patterns
            if company_patterns:
                logger.info("\nCompany Patterns:")
                sorted_companies = sorted(company_patterns.items(), key=lambda x: x[1], reverse=True)
                for company, count in sorted_companies[:10]:  # Top 10 companies
                    percentage = (count / total_emails) * 100
                    logger.info(f"{company}: {count} occurrences ({percentage:.1f}%)")
            
            # Analyze position patterns
            position_patterns = {}
            for result in all_results:
                position = result['Position']
                if position and position != 'Unknown Position':
                    position_patterns[position] = position_patterns.get(position, 0) + 1
            
            # Log position patterns
            if position_patterns:
                logger.info("\nPosition Patterns:")
                sorted_positions = sorted(position_patterns.items(), key=lambda x: x[1], reverse=True)
                for position, count in sorted_positions[:10]:  # Top 10 positions
                    percentage = (count / total_emails) * 100
                    logger.info(f"{position}: {count} occurrences ({percentage:.1f}%)")
            
            # Analyze status patterns
            status_patterns = {}
            for result in all_results:
                status = result['Status']
                if status:
                    status_patterns[status] = status_patterns.get(status, 0) + 1
            
            # Log status patterns
            if status_patterns:
                logger.info("\nStatus Patterns:")
                sorted_statuses = sorted(status_patterns.items(), key=lambda x: x[1], reverse=True)
                for status, count in sorted_statuses:
                    percentage = (count / total_emails) * 100
                    logger.info(f"{status}: {count} occurrences ({percentage:.1f}%)")
            
            # Suggest improvements
            logger.info("\nSuggested Improvements:")
            
            # Check keyword effectiveness
            all_keywords = []
            for result in all_results:
                keywords = result['Matched Keywords'].split(',')
                all_keywords.extend([k.strip() for k in keywords if k.strip()])
            
            keyword_freq = {}
            for keyword in all_keywords:
                keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
            
            # Find potentially missing keywords
            high_confidence_jobs = [r for r in all_results if r['Is Job Related'].lower() == 'true' and float(r['Confidence']) >= 0.8]
            if high_confidence_jobs:
                logger.info("\nHigh Confidence Job Emails without Strong Keywords:")
                for result in high_confidence_jobs[:5]:
                    logger.info(f"Subject: {result['Subject']}")
                    logger.info(f"From: {result['From']}")
                    logger.info(f"Confidence: {result['Confidence']}")
            
            # Check for patterns in false positives
            false_positives = [r for r in all_results if r['Is Job Related'].lower() == 'true' and float(r['Confidence']) < 0.5]
            if false_positives:
                logger.info("\nPatterns in False Positives:")
                for result in false_positives[:5]:
                    logger.info(f"Subject: {result['Subject']}")
                    logger.info(f"From: {result['From']}")
                    logger.info(f"Confidence: {result['Confidence']}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing log files: {str(e)}")
            return None

    @staticmethod
    def _get_cached_email(email_id, user_id):
        """Get cached email analysis result"""
        try:
            cache_key = f"{user_id}_{email_id}"
            cached_data = EmailService._analysis_cache.get(cache_key)
            if cached_data:
                return cached_data
            return None
        except Exception as e:
            logger.error(f"Error getting cached email: {str(e)}")
            return None

    @staticmethod
    def _cache_email(email_id, user_id, analysis_data):
        """Cache email analysis result"""
        try:
            cache_key = f"{user_id}_{email_id}"
            EmailService._analysis_cache[cache_key] = analysis_data
        except Exception as e:
            logger.error(f"Error caching email: {str(e)}")

    @staticmethod
    def _clear_cache():
        """Clear all caches"""
        try:
            EmailService._cache.clear()
            EmailService._email_cache.clear()
            EmailService._analysis_cache.clear()
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")

    @staticmethod
    def _cleanup_expired_cache():
        """Clean up expired cache entries"""
        try:
            current_time = time.time()
            # Clean up email cache
            EmailService._email_cache = {
                k: v for k, v in EmailService._email_cache.items()
                if current_time - v.get('timestamp', 0) < EmailService._email_cache_ttl
            }
            # Clean up analysis cache
            EmailService._analysis_cache = {
                k: v for k, v in EmailService._analysis_cache.items()
                if current_time - v.get('timestamp', 0) < EmailService._cache_ttl
            }
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}")

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
            # Create an SSL context with certificate verification and modern protocols
            context = ssl.create_default_context()
            context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3  # Disable older protocols
            context.minimum_version = ssl.TLSVersion.TLSv1_2  # Require TLS 1.2 or higher
            
            # Test connection
            imap = imaplib.IMAP4_SSL('imap.mail.yahoo.com', ssl_context=context)
            imap.login(yahoo_email, app_password)
            imap.select('INBOX')
            imap.close()
            imap.logout()
            
            # Get user
            user = User.get_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Update user's email connection
            update_data = {
                'email_connected': True,
                'connected_email': yahoo_email,
                'email_provider': 'yahoo',
                'email_password': app_password,
                'email_settings': {
                    'auto_scan': True,
                    'require_approval': True,
                    'scan_attachments': False,
                    'last_scan': None
                }
            }
            
            mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            
            return True, "Successfully connected to Yahoo Mail"
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP error: {str(e)}")
            return False, f"Failed to connect to Yahoo Mail: {str(e)}"
        except Exception as e:
            logger.error(f"Error connecting to Yahoo Mail: {str(e)}")
            return False, f"Failed to connect to Yahoo Mail: {str(e)}"
    
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
            result = EmailService._scan_yahoo_imap(user)
            success = result.get('success', False)
            if success:
                job_applications = result.get('job_applications', [])
                # Update last scan time
                user.last_email_scan = datetime.utcnow()
                user.save()
            else:
                return False, result.get('message', 'Error scanning Yahoo Mail'), "main.email_suggestions"
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
        
        for keyword in APPLICATION_KEYWORDS['general_indicators']:
            if keyword.lower() in combined_text:
                keyword_count += 1
                matched_keywords.append(keyword)
                
                # If we find a strong indicator phrase (multi-word), give it more weight
                if len(keyword.split()) > 1:
                    keyword_count += 1
        
        # Check for status-specific keywords which also indicate job-relatedness
        for status, keywords in APPLICATION_KEYWORDS['status_indicators'].items():
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
        """
        Extract job position from email subject and body
        """
        try:
            # First try to extract from subject
            subject_patterns = [
                r'(?:position|role|job|opportunity)(?:\s+for)?\s+(?:of\s+)?([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))',
                r'([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))\s+(?:position|role|job|opportunity)',
                r'(?:applying|application|candidacy)\s+for\s+([A-Za-z0-9\s]+)',
                r'(?:looking for|seeking|hiring)\s+([A-Za-z0-9\s]+)',
                r'([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))(?:\s+at|\s+with|\s+for)?\s+[A-Za-z0-9\s]+',
                r'[A-Za-z0-9\s]+(?:\s+at|\s+with|\s+for)?\s+([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))'
            ]
            
            for pattern in subject_patterns:
                match = re.search(pattern, subject)
                if match:
                    position = match.group(1).strip()
                    if position and position.lower() not in ['details', 'terms', 'conditions', 'privacy', 'policy', 'updates']:
                        logger.info(f"Extracted position from subject: {position}")
                        return position
            
            # If not found in subject, try body
            body_patterns = [
                r'(?:position|role|job|opportunity)(?:\s+for)?\s+(?:of\s+)?([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))',
                r'([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))\s+(?:position|role|job|opportunity)',
                r'(?:applying|application|candidacy)\s+for\s+([A-Za-z0-9\s]+)',
                r'(?:looking for|seeking|hiring)\s+([A-Za-z0-9\s]+)',
                r'([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))(?:\s+at|\s+with|\s+for)?\s+[A-Za-z0-9\s]+',
                r'[A-Za-z0-9\s]+(?:\s+at|\s+with|\s+for)?\s+([A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))'
            ]
            
            for pattern in body_patterns:
                match = re.search(pattern, body)
                if match:
                    position = match.group(1).strip()
                    if position and position.lower() not in ['details', 'terms', 'conditions', 'privacy', 'policy', 'updates']:
                        logger.info(f"Extracted position from body: {position}")
                        return position
            
            # If still not found, try to extract from company name in subject
            company_pattern = r'([A-Za-z0-9\s]+(?:\s+at|\s+with|\s+for)?\s+[A-Za-z0-9\s]+(?:Developer|Engineer|Manager|Designer|Analyst|Specialist|Director|Coordinator|Assistant|Administrator|Consultant|Architect|Lead|Senior|Junior|Principal|Staff|Head|Chief|Officer|President|Vice President|VP|CEO|CTO|CFO|COO|CIO|Founder|Co-founder|Partner|Associate|Intern|Trainee|Apprentice))'
            match = re.search(company_pattern, subject)
            if match:
                position = match.group(1).strip()
                if position and position.lower() not in ['details', 'terms', 'conditions', 'privacy', 'policy', 'updates']:
                    logger.info(f"Extracted position from company name in subject: {position}")
                    return position
            
            logger.info("No position found in email")
            return "Not specified"
            
        except Exception as e:
            logger.error(f"Error extracting position: {str(e)}")
            return "Not specified"

    @staticmethod
    def _extract_job_url(subject, body):
        """
        Extract job posting URL from email subject and body
        """
        try:
            # Common URL patterns in job-related emails
            url_patterns = [
                r'https?://(?:www\.)?(?:linkedin\.com|indeed\.com|glassdoor\.com|monster\.com|careerbuilder\.com|ziprecruiter\.com|dice\.com|hired\.com|angellist\.com|wellfound\.com|lever\.co|greenhouse\.io|workday\.com|jobvite\.com|smartrecruiters\.com|taleo\.net|applicanttracking\.com|recruiter\.com|talent\.com|hiring\.com|careers\.com|jobs\.com|employment\.com|staffing\.com|headhunter\.com)/[^\s<>"]+',
                r'https?://(?:www\.)?[^\s<>"]+\.(?:com|org|net|io|co|ai|dev)/[^\s<>"]+',
                r'https?://[^\s<>"]+'
            ]
            
            # First try to find URLs in the subject
            for pattern in url_patterns:
                matches = re.findall(pattern, subject)
                if matches:
                    # Filter out common non-job URLs
                    for url in matches:
                        if not any(x in url.lower() for x in ['unsubscribe', 'update', 'preferences', 'settings', 'profile', 'terms', 'privacy', 'policy']):
                            logger.info(f"Found job URL in subject: {url}")
                            return url
            
            # If not found in subject, try body
            for pattern in url_patterns:
                matches = re.findall(pattern, body)
                if matches:
                    # Filter out common non-job URLs
                    for url in matches:
                        if not any(x in url.lower() for x in ['unsubscribe', 'update', 'preferences', 'settings', 'profile', 'terms', 'privacy', 'policy']):
                            logger.info(f"Found job URL in body: {url}")
                            return url
            
            logger.info("No job URL found in email")
            return "https://example.com/job-posting"  # Default URL
            
        except Exception as e:
            logger.error(f"Error extracting job URL: {str(e)}")
            return "https://example.com/job-posting"  # Default URL
    
    @staticmethod
    def _determine_status(subject, body):
        """
        Determine application status from email content with enhanced keyword detection
        """
        combined_text = (subject + " " + body).lower()
        
        # Check for each status type
        status_scores = {}
        
        for status, keywords in APPLICATION_KEYWORDS['status_indicators'].items():
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
        """Schedule cache cleanup task."""
        def cleanup():
            while True:
                EmailService._cleanup_expired_cache()
                time.sleep(3600)  # Run every hour

        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()

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