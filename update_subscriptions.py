import sys
import os
from datetime import datetime, timedelta
from job_app_tracker import create_app
from job_app_tracker.config.mongodb import mongo

def update_subscriptions():
    """Update existing users with subscription information"""
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Update all users without subscription
        result = mongo.db.users.update_many(
            {'subscription': {'$exists': False}},
            {'$set': {
                'subscription': {
                    'is_premium': False,
                    'plan': 'free',
                    'start_date': None,
                    'end_date': None,
                    'payment_id': None
                }
            }}
        )
        
        print(f"Updated {result.modified_count} users with default subscription")
        
        # Make naeimsalib@yahoo.com premium
        result = mongo.db.users.update_one(
            {'email': 'naeimsalib@yahoo.com'},
            {'$set': {
                'subscription': {
                    'is_premium': True,
                    'plan': 'premium',
                    'start_date': datetime.now(),
                    'end_date': datetime.now() + timedelta(days=36500),  # 100 years
                    'payment_id': 'test_account'
                }
            }}
        )
        
        print(f"Updated naeimsalib@yahoo.com: {result.modified_count} document modified")
        
        # Create analysis_cache collection if it doesn't exist
        if 'analysis_cache' not in mongo.db.list_collection_names():
            mongo.db.create_collection('analysis_cache')
            print("Created analysis_cache collection")
            
        # Create scan_logs collection if it doesn't exist
        if 'scan_logs' not in mongo.db.list_collection_names():
            mongo.db.create_collection('scan_logs')
            print("Created scan_logs collection")
            
        print("Database update complete")

if __name__ == "__main__":
    update_subscriptions() 