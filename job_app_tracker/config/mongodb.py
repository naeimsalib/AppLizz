import os
from flask_pymongo import PyMongo
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
import certifi
import threading

# Create a global PyMongo instance
mongo = PyMongo()

# Initialize MongoDB with the URI from environment variables
def init_mongodb(app):
    try:
        # Get MongoDB URI and add SSL certificate path
        uri = os.getenv("MONGODB_URI")
        
        # Add connection pooling and timeout settings
        if "?" in uri:
            uri += "&tlsCAFile=" + certifi.where()
            uri += "&maxPoolSize=10&connectTimeoutMS=5000&socketTimeoutMS=30000"
        else:
            uri += "?tlsCAFile=" + certifi.where()
            uri += "&maxPoolSize=10&connectTimeoutMS=5000&socketTimeoutMS=30000"
            
        app.config["MONGO_URI"] = uri
        
        # Initialize PyMongo
        mongo.init_app(app)
        
        # Test connection
        with app.app_context():
            mongo.db.command('ping')
            
            # Create indexes in a background thread to avoid blocking startup
            def create_indexes():
                with app.app_context():
                    try:
                        mongo.db.users.create_index("email", unique=True, background=True)
                        mongo.db.applications.create_index([("user_id", 1), ("date_applied", -1)], background=True)
                        logging.info("MongoDB indexes created successfully")
                    except OperationFailure as e:
                        logging.warning(f"Error creating indexes: {str(e)}")
            
            # Start index creation in background
            threading.Thread(target=create_indexes, daemon=True).start()
        
        return mongo
    except ConnectionFailure as e:
        logging.error(f"Failed to connect to MongoDB: {str(e)}")
        raise 