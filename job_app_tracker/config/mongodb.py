import os
from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
import certifi

# Create a global PyMongo instance
mongo = PyMongo()

# Initialize MongoDB with the URI from environment variables
def init_mongodb(app):
    try:
        # Set MongoDB URI from environment variable or use default
        app.config['MONGO_URI'] = os.getenv('MONGODB_URI', 'mongodb://naeimsalib:Naeim2002@cluster0.aqbhxvj.mongodb.net/job_tracker?retryWrites=true&w=majority')
        
        # Initialize PyMongo with the app
        mongo.init_app(app)
        
        # Test connection
        with app.app_context():
            mongo.db.command('ping')
            
            # Create indexes if they don't exist
            try:
                # Create case-insensitive unique index for email
                mongo.db.users.create_index([("email", 1)], unique=True, collation={'locale': 'en', 'strength': 2})
                
                # Create other indexes
                mongo.db.applications.create_index([("user_id", 1), ("date_applied", -1)])
                logging.info("MongoDB indexes created successfully")
            except OperationFailure as e:
                logging.warning(f"Error creating indexes: {str(e)}")
        
        return mongo
    except ConnectionFailure as e:
        logging.error(f"Failed to connect to MongoDB: {str(e)}")
        raise 