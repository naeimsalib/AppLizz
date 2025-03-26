import os
from datetime import timedelta

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("No SECRET_KEY set for Flask application")

# Session configuration
PERMANENT_SESSION_LIFETIME = timedelta(days=7)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Security headers
STRICT_TRANSPORT_SECURITY = True
STRICT_TRANSPORT_SECURITY_INCLUDE_SUBDOMAINS = True
STRICT_TRANSPORT_SECURITY_PRELOAD = True

# MongoDB configuration
MONGODB_URI = os.environ.get('MONGODB_URI')
if not MONGODB_URI:
    raise ValueError("No MONGODB_URI set for Flask application")

# File upload configuration
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# CSRF protection
WTF_CSRF_ENABLED = True
WTF_CSRF_SSL_STRICT = True
WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

# Cache configuration
SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year
STATIC_FOLDER = 'static'

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# Rate limiting
RATELIMIT_ENABLED = True
RATELIMIT_STORAGE_URL = "memory://"
RATELIMIT_DEFAULT = "100 per day"
RATELIMIT_STRATEGY = "fixed-window"

# Error pages
ERROR_404_HELP = False
ERROR_INCLUDE_MESSAGE = False

# Production specific settings
ENV = 'production'
DEBUG = False
TESTING = False
PROPAGATE_EXCEPTIONS = False 