import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
    TESTING = os.environ.get('TESTING', 'True').lower() == 'true'
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/job_tracker') 