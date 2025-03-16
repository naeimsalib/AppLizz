import os
import sys
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import certifi
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

# Connect to MongoDB
mongo_uri = os.environ.get('MONGODB_URI')
if not mongo_uri:
    print("Error: MONGODB_URI environment variable not found")
    sys.exit(1)

# Add SSL certificate path
if "?" in mongo_uri:
    mongo_uri += "&tlsCAFile=" + certifi.where()
else:
    mongo_uri += "?tlsCAFile=" + certifi.where()

client = MongoClient(mongo_uri)
db = client.get_database()

def main():
    # Get the user ID from the email suggestions
    suggestion = db.email_suggestions.find_one()
    if not suggestion:
        print("No email suggestions found")
        return
    
    user_id = suggestion.get('user_id')
    print(f"User ID: {user_id}")
    
    # Get the user's email settings
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        print(f"User with ID {user_id} not found")
        return
    
    print(f"Email: {user.get('email')}")
    print(f"Email connected: {user.get('email_connected')}")
    print(f"Connected email: {user.get('connected_email')}")
    print(f"Email provider: {user.get('email_provider')}")
    
    # Check email settings
    email_settings = user.get('email_settings', {})
    print("\nEmail Settings:")
    print(f"Require approval: {email_settings.get('require_approval', True)}")
    print(f"Last scan: {email_settings.get('last_scan')}")
    
    # Print all email settings
    print("\nAll Email Settings:")
    for key, value in email_settings.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main() 