from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from job_app_tracker.config.mongodb import mongo
from bson.objectid import ObjectId
from datetime import datetime

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
        self.email_settings = user_data.get('email_settings', {
            'auto_scan': True,
            'require_approval': True,
            'scan_attachments': False,
            'last_scan': None
        })
        
    @staticmethod
    def create_user(email, password, name):
        """Create a new user"""
        # Convert email to lowercase before storing
        email = email.lower()
        
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
            'created_at': datetime.now()
        }
        result = mongo.db.users.insert_one(user_data)
        user_data['_id'] = result.inserted_id
        return User(user_data)
    
    @staticmethod
    def get_by_email(email):
        """Get user by email (case-insensitive)"""
        # Convert email to lowercase for comparison
        email = email.lower() if email else None
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
            'email_token_expiry': None
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
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'email_connected': self.email_connected,
            'connected_email': self.connected_email,
            'email_provider': self.email_provider
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