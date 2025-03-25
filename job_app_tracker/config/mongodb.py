import os
from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
import certifi

# Create a global PyMongo instance
mongo = PyMongo()

def init_db(app):
    """Initialize MongoDB connection"""
    try:
        # Use environment variable for connection URI
        app.config['MONGO_URI'] = app.config.get('MONGODB_URI')
        
        # Check if we're using a localhost connection
        is_local = 'localhost' in app.config['MONGO_URI'] or '127.0.0.1' in app.config['MONGO_URI']
        
        if is_local:
            # For local connections, don't use SSL
            mongo.init_app(app)
        else:
            # For cloud connections, use SSL certification
            mongo.init_app(app, tlsCAFile=certifi.where())
        
        # Test connection
        with app.app_context():
            mongo.db.command('ping')
            logging.info("MongoDB connection successful")
            
            # Create indexes if they don't exist
            try:
                # Create indexes for users collection
                mongo.db.users.create_index('email', unique=True)
                mongo.db.users.create_index('username', unique=True)
                
                # Create indexes for applications collection
                mongo.db.applications.create_index('user_id')
                mongo.db.applications.create_index([('user_id', 1), ('status', 1)])
                mongo.db.applications.create_index([('user_id', 1), ('date_applied', -1)])
                
                logging.info("MongoDB indexes created successfully")
            except OperationFailure as e:
                logging.warning(f"Error creating indexes: {str(e)}")
        
        return mongo
    except ConnectionFailure as e:
        logging.error(f"Failed to connect to MongoDB: {str(e)}")
        raise 