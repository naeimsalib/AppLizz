import os
from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv
from flask import current_app

# Load environment variables from the root directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# Create a global PyMongo instance
mongo = PyMongo()

def init_mongodb(app):
    """Initialize MongoDB connection"""
    try:
        # Get MongoDB URI from environment variable
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MongoDB URI not found in environment variables")
        
        logging.info(f"MongoDB URI: {mongodb_uri}")
        
        # Configure MongoDB URI in Flask app
        app.config['MONGO_URI'] = mongodb_uri
        
        # Initialize PyMongo with the app
        mongo.init_app(app)
        
        # Test the connection
        mongo.db.command('ping')
        logging.info("Successfully connected to MongoDB")
        
        # Create indexes
        create_indexes(mongo.db)
        
        return mongo
        
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {str(e)}")
        logging.error("Please check your MONGODB_URI environment variable and ensure it's correct")
        logging.error("Also verify that your IP address is whitelisted in MongoDB Atlas")
        raise

def create_indexes(db):
    """Create necessary indexes"""
    try:
        # Create case-insensitive unique index for email in users collection
        db.users.create_index(
            [("email", 1)],
            unique=True,
            collation={'locale': 'en', 'strength': 2}
        )
        
        # Create indexes for applications collection
        db.applications.create_index([("user_id", 1)])
        db.applications.create_index([("status", 1)])
        db.applications.create_index([("date_applied", -1)])
        
        logging.info("MongoDB indexes created successfully")
    except Exception as e:
        logging.warning(f"Error creating indexes: {str(e)}")

# Initialize MongoDB with the URI from environment variables
def init_mongodb_old(app):
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