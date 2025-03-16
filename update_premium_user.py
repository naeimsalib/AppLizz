import sys
import os
from datetime import datetime, timedelta
from job_app_tracker import create_app
from job_app_tracker.config.mongodb import mongo
from bson.objectid import ObjectId
import re

def update_premium_user(email):
    """Update a specific user to have a permanent premium subscription"""
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Find the user by email (case-insensitive)
        # Create a case-insensitive regex pattern
        email_pattern = re.compile(f"^{re.escape(email)}$", re.IGNORECASE)
        user = mongo.db.users.find_one({'email': email_pattern})
        
        if not user:
            print(f"User with email {email} not found")
            return
        
        # Update the user's subscription to premium with a 100-year expiration
        result = mongo.db.users.update_one(
            {'_id': user['_id']},
            {'$set': {
                'subscription': {
                    'is_premium': True,
                    'plan': 'premium',
                    'start_date': datetime.now(),
                    'end_date': datetime.now() + timedelta(days=36500),  # 100 years
                    'payment_id': 'permanent_premium_account'
                }
            }}
        )
        
        print(f"Updated user {user['email']}: {result.modified_count} document modified")
        
        # Verify the update
        updated_user = mongo.db.users.find_one({'_id': user['_id']})
        if updated_user and updated_user.get('subscription', {}).get('is_premium'):
            print(f"User {updated_user['email']} is now a premium user until {updated_user['subscription']['end_date'].strftime('%Y-%m-%d')}")
        else:
            print(f"Failed to update user {user['email']} to premium status")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input("Enter the email address of the user to update: ")
    
    update_premium_user(email) 