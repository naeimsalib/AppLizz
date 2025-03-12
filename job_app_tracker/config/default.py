import os

# Flask configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
DEBUG = True

# MongoDB configuration
MONGO_URI = "mongodb://localhost:27017/job_tracker"

# Application configuration
TESTING = False
SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_DURATION = 3600  # 1 hour 