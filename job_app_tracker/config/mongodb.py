import os
from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a global PyMongo instance
mongo = PyMongo()

# Initialize MongoDB with the URI from environment variables
def init_mongodb(app):
    try:
        # Set MongoDB URI from environment variable or use default
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI environment variable is not set")
            
        logging.info(f"Using MongoDB URI: {mongodb_uri}")
        app.config['MONGO_URI'] = mongodb_uri
        
        # Set SSL certificate verification
        app.config['MONGO_OPTIONS'] = {
            'tlsCAFile': certifi.where(),
            'connect': True,
            'serverSelectionTimeoutMS': 5000
        }
        
        # Try direct connection first
        try:
            logging.info("Attempting direct MongoDB connection...")
            client = MongoClient(mongodb_uri, tlsCAFile=certifi.where())
            client.admin.command('ping')
            client.close()
            logging.info("Successfully tested MongoDB connection")
        except Exception as e:
            logging.error(f"Direct connection test failed: {str(e)}")
            raise
        
        # Initialize PyMongo with the app
        mongo.init_app(app)
        
        # Test connection and create indexes
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