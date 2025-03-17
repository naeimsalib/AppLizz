from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from job_app_tracker.config.mongodb import mongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id', ''))
        self.email = user_data.get('email')
        self.password_hash = user_data.get('password_hash')
        self.name = user_data.get('name')
        
        # Email integration fields
        self.email_connected = user_data.get('email_connected', False)
        self.connected_email = user_data.get('connected_email')
        self.email_provider = user_data.get('email_provider')
        self.email_token = user_data.get('email_token')
        self.email_refresh_token = user_data.get('email_refresh_token')
        self.email_token_expiry = user_data.get('email_token_expiry')
        self.email_password = user_data.get('email_password')
        self.email_settings = user_data.get('email_settings', {
            'auto_scan': True,
            'require_approval': True,
            'scan_attachments': False,
            'last_scan': None
        })
        
        # Subscription fields
        self.subscription = user_data.get('subscription', {
            'is_premium': False,
            'plan': 'free',
            'start_date': None,
            'end_date': None,
            'payment_id': None
        })
        
        self._is_premium = user_data.get('is_premium', False)
        self.last_email_scan = user_data.get('last_email_scan')
        self.email_credentials = user_data.get('email_credentials')
        self.created_at = user_data.get('created_at', datetime.utcnow())
        self.updated_at = user_data.get('updated_at', datetime.utcnow())
        self.last_processed_email_id = user_data.get('last_processed_email_id')
        self.email_cache = user_data.get('email_cache', {})
        self.email_cache_ttl = user_data.get('email_cache_ttl', 7)  # Cache TTL in days
        
    @property
    def is_premium(self):
        """Check if user has an active premium subscription"""
        if not self.subscription:
            return False
            
        # Special case for naeimsalib@yahoo.com - always premium
        if self.email == 'naeimsalib@yahoo.com':
            return True
            
        # Check if subscription is active
        is_premium = self.subscription.get('is_premium', False)
        end_date = self.subscription.get('end_date')
        
        if not is_premium or not end_date:
            return False
            
        # Check if subscription has expired
        return end_date > datetime.utcnow()
        
    @staticmethod
    def create_user(email, password, name):
        """Create a new user"""
        user_data = {
            'email': email,
            'password_hash': generate_password_hash(password),
            'name': name,
            'email_connected': False,
            'email_settings': {
                'auto_scan': True,
                'require_approval': True,
                'scan_attachments': False,
                'last_scan': None
            },
            'subscription': {
                'is_premium': False,
                'plan': 'free',
                'start_date': None,
                'end_date': None,
                'payment_id': None
            },
            'created_at': datetime.now()
        }
        
        # Special case for naeimsalib@yahoo.com - make premium with no expiration
        if email == 'naeimsalib@yahoo.com':
            user_data['subscription'] = {
                'is_premium': True,
                'plan': 'premium',
                'start_date': datetime.now(),
                'end_date': datetime.now() + timedelta(days=36500),  # 100 years
                'payment_id': 'test_account'
            }
            
        result = mongo.db.users.insert_one(user_data)
        user_data['_id'] = result.inserted_id
        return User(user_data)
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        user_data = mongo.db.users.find_one({'email': email})
        return User(user_data) if user_data else None
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        try:
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            return User(user_data) if user_data else None
        except:
            return None
    
    def check_password(self, password):
        """Check if password is correct"""
        return check_password_hash(self.password_hash, password)
    
    def update_email_connection(self, connected_email, provider, token, refresh_token, expiry):
        """Update email connection details"""
        update_data = {
            'email_connected': True,
            'connected_email': connected_email,
            'email_provider': provider,
            'email_token': token,
            'email_refresh_token': refresh_token,
            'email_token_expiry': expiry
        }
        
        mongo.db.users.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': update_data}
        )
        
        # Update local attributes
        self.email_connected = True
        self.connected_email = connected_email
        self.email_provider = provider
        self.email_token = token
        self.email_refresh_token = refresh_token
        self.email_token_expiry = expiry
        
        return True
    
    def disconnect_email(self):
        """Disconnect email integration"""
        update_data = {
            'email_connected': False,
            'connected_email': None,
            'email_provider': None,
            'email_token': None,
            'email_refresh_token': None,
            'email_token_expiry': None,
            'email_password': None
        }
        
        mongo.db.users.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': update_data}
        )
        
        # Update local attributes
        self.email_connected = False
        self.connected_email = None
        self.email_provider = None
        self.email_token = None
        self.email_refresh_token = None
        self.email_token_expiry = None
        self.email_password = None
        
        return True
    
    def update_email_settings(self, settings):
        """Update email scanning settings"""
        update_data = {
            'email_settings': settings
        }
        
        mongo.db.users.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': update_data}
        )
        
        # Update local attributes
        self.email_settings = settings
        
        return True
        
    def update_subscription(self, is_premium, plan, start_date, end_date, payment_id):
        """Update subscription details"""
        subscription = {
            'is_premium': is_premium,
            'plan': plan,
            'start_date': start_date,
            'end_date': end_date,
            'payment_id': payment_id
        }
        
        mongo.db.users.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': {'subscription': subscription}}
        )
        
        # Update local attributes
        self.subscription = subscription
        
        return True
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'email_connected': self.email_connected,
            'connected_email': self.connected_email,
            'email_provider': self.email_provider,
            'is_premium': self.is_premium,
            'plan': self.subscription.get('plan', 'free') if self.subscription else 'free'
        }
        
    @property
    def has_suggestions(self):
        """Check if user has unprocessed email suggestions"""
        # Check if there are any unprocessed suggestions
        count = mongo.db.email_suggestions.count_documents({
            'user_id': str(self.id),
            'processed': False
        })
        
        return count > 0

    def save(self):
        """Save user data to database."""
        user_data = {
            'email': self.email,
            'password_hash': self.password_hash,
            'subscription': self.subscription,  # Save subscription data instead of is_premium
            'connected_email': self.connected_email,
            'email_password': self.email_password,
            'last_email_scan': self.last_email_scan,
            'email_provider': self.email_provider,
            'email_credentials': self.email_credentials,
            'last_processed_email_id': self.last_processed_email_id,
            'email_cache': self.email_cache,
            'email_cache_ttl': self.email_cache_ttl,
            'email_settings': self.email_settings,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            mongo.db.users.update_one(
                {'_id': ObjectId(self.id)},
                {'$set': user_data}
            )
        else:
            result = mongo.db.users.insert_one(user_data)
            self.id = str(result.inserted_id)
        
        return self

    def update_last_processed_email(self, email_id):
        """Update the last processed email ID."""
        self.last_processed_email_id = email_id
        self.save()

    def update_last_scan(self):
        """Update the last email scan timestamp."""
        self.last_email_scan = datetime.utcnow()
        self.save()

    def clear_email_cache(self):
        """Clear the email cache."""
        self.email_cache = {}
        self.save() 