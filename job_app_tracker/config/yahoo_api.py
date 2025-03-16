"""
Yahoo Mail API Configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Yahoo OAuth Configuration
YAHOO_CLIENT_ID = os.environ.get('YAHOO_CLIENT_ID', '')
YAHOO_CLIENT_SECRET = os.environ.get('YAHOO_CLIENT_SECRET', '')
YAHOO_REDIRECT_URI = os.environ.get('YAHOO_REDIRECT_URI', 'https://applizz.com/email/callback/yahoo')

# Yahoo Mail API Endpoints
YAHOO_AUTH_URL = 'https://api.login.yahoo.com/oauth2/request_auth'
YAHOO_TOKEN_URL = 'https://api.login.yahoo.com/oauth2/get_token'
YAHOO_API_BASE_URL = 'https://mail.yahooapis.com/v1'

# Yahoo Mail API Scopes
YAHOO_SCOPES = 'email'  # Try using just the email scope which is documented as supported

# Email Classification Keywords
APPLICATION_KEYWORDS = [
    'application', 'job', 'position', 'resume', 'cv', 'candidate', 'opportunity',
    'applied', 'hiring', 'recruitment', 'talent', 'career', 'employment'
]

INTERVIEW_KEYWORDS = [
    'interview', 'meeting', 'schedule', 'discuss', 'conversation', 'talk',
    'assessment', 'evaluation', 'screening', 'technical', 'coding', 'test'
]

REJECTION_KEYWORDS = [
    'unfortunately', 'regret', 'not moving forward', 'not selected', 'other candidates',
    'not proceeding', 'decided to pursue', 'not a match', 'not the right fit',
    'thank you for your interest', 'position has been filled'
]

OFFER_KEYWORDS = [
    'offer', 'congratulations', 'pleased to inform', 'welcome aboard', 'join our team',
    'compensation', 'salary', 'benefits', 'start date', 'onboarding'
] 