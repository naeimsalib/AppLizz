import os
from job_app_tracker import create_app
from job_app_tracker.config.mongodb import mongo

def list_users():
    """List all users in the database"""
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Find all users
        users = list(mongo.db.users.find())
        
        if not users:
            print("No users found in the database")
            return
        
        print(f"Found {len(users)} users:")
        for user in users:
            email = user.get('email', 'No email')
            is_premium = user.get('subscription', {}).get('is_premium', False)
            end_date = user.get('subscription', {}).get('end_date', 'No end date')
            
            print(f"Email: {email}")
            print(f"Premium: {is_premium}")
            print(f"Subscription end date: {end_date}")
            print("-" * 30)

if __name__ == "__main__":
    list_users() 