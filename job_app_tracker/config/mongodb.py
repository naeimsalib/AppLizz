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
        # Get MongoDB URI and add SSL certificate path
        uri = os.getenv("MONGODB_URI")
        if "?" in uri:
            uri += "&tlsCAFile=" + certifi.where()
        else:
            uri += "?tlsCAFile=" + certifi.where()
            
        app.config["MONGO_URI"] = uri
        
        # Initialize PyMongo
        mongo.init_app(app)
        
        # Test connection
        with app.app_context():
            mongo.db.command('ping')
            
            # Create indexes if they don't exist
            try:
                mongo.db.users.create_index("email", unique=True)
                mongo.db.applications.create_index([("user_id", 1), ("date_applied", -1)])
                logging.info("MongoDB indexes created successfully")
            except OperationFailure as e:
                logging.warning(f"Error creating indexes: {str(e)}")
        
        return mongo
    except ConnectionFailure as e:
        logging.error(f"Failed to connect to MongoDB: {str(e)}")
        raise 