import os
import sys
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import certifi

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
    # Check email suggestions
    suggestions_count = db.email_suggestions.count_documents({})
    print(f"Email suggestions count: {suggestions_count}")
    
    if suggestions_count > 0:
        print("\nLatest 5 email suggestions:")
        suggestions = list(db.email_suggestions.find().sort("created_at", -1).limit(5))
        for suggestion in suggestions:
            print(f"User ID: {suggestion.get('user_id')}")
            print(f"Created at: {suggestion.get('created_at')}")
            print(f"Processed: {suggestion.get('processed')}")
            print(f"Suggestions count: {len(suggestion.get('suggestions', []))}")
            print("---")
    
    # Check applications
    applications_count = db.applications.count_documents({})
    print(f"\nApplications count: {applications_count}")
    
    if applications_count > 0:
        print("\nLatest 5 applications:")
        applications = list(db.applications.find().sort("created_at", -1).limit(5))
        for app in applications:
            print(f"Company: {app.get('company')}")
            print(f"Position: {app.get('position')}")
            print(f"Status: {app.get('status')}")
            print(f"Created at: {app.get('created_at')}")
            print("---")

if __name__ == "__main__":
    main() 