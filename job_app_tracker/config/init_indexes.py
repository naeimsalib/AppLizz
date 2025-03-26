import logging
from flask import current_app
from pymongo.errors import OperationFailure
from job_app_tracker.config.mongodb import mongo

def init_indexes():
    """Initialize MongoDB indexes"""
    try:
        # Create indexes for users collection
        mongo.db.users.create_index([('email', 1)], unique=True, collation={'locale': 'en', 'strength': 2})  # Case-insensitive
        mongo.db.users.create_index([('username', 1)], unique=True, sparse=True)  # Allow null usernames
        
        # Create indexes for applications collection
        mongo.db.applications.create_index('user_id')
        mongo.db.applications.create_index([('user_id', 1), ('status', 1)])
        mongo.db.applications.create_index([('user_id', 1), ('date_applied', -1)])
        
        # Create indexes for interviews collection
        mongo.db.interviews.create_index([('application_id', 1), ('date', 1)])
        
        logging.info("MongoDB indexes created successfully")
    except OperationFailure as e:
        if 'already exists' not in str(e):
            logging.error(f"Error creating indexes: {str(e)}")
            raise
        logging.info("Indexes already exist") 