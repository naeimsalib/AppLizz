import os

# Flask configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
DEBUG = False  # Disable debug mode by default for better performance

# MongoDB configuration
MONGO_URI = "mongodb://localhost:27017/job_tracker"

# Application configuration
TESTING = False
SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_DURATION = 3600  # 1 hour

# Performance optimizations
SEND_FILE_MAX_AGE_DEFAULT = 31536000  # Cache static files for 1 year
TEMPLATES_AUTO_RELOAD = False  # Disable template auto-reload for production
PREFERRED_URL_SCHEME = 'http'  # Use http by default (change to https in production) 