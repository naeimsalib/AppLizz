from flask_login import UserMixin
import bcrypt
from job_app_tracker.config.mongodb import mongo
from bson import ObjectId
from datetime import datetime

class User(UserMixin):
    def __init__(self, data):
        self.id = str(data.get('_id', ''))
        self.email = data.get('email', '')
        self.name = data.get('name', '')
        self.password_hash = data.get('password_hash', '')
        self.email_settings = data.get('email_settings', {})
        self.email_connected = data.get('email_connected', False)
        self.connected_email = data.get('connected_email')
        self.email_provider = data.get('email_provider')
        self.email_token = data.get('email_token')
        self.email_refresh_token = data.get('email_refresh_token')
        self.email_token_expiry = data.get('email_token_expiry')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        
    @classmethod
    def get_by_email(cls, email):
        # Convert email to lowercase before searching
        email = email.lower()
        data = mongo.db.users.find_one({'email': email})
        return cls(data) if data else None

    @classmethod
    def create(cls, data):
        # Convert email to lowercase before creating
        data['email'] = data['email'].lower()
        result = mongo.db.users.insert_one(data)
        data['_id'] = result.inserted_id
        return cls(data)

    def update(self, data):
        result = mongo.db.users.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': data}
        )
        if result.modified_count > 0:
            for key, value in data.items():
                setattr(self, key, value)
            return True
        return False

    def disconnect_email(self):
        update_data = {
            'email_connected': False,
            'connected_email': None,
            'email_provider': None,
            'email_token': None,
            'email_refresh_token': None,
            'email_token_expiry': None,
            'email_settings': {}
        }
        return self.update(update_data)

    @staticmethod
    def create_user(email, password, name):
        """Create a new user"""
        # Convert email to lowercase before storing
        email = email.lower()
        
        # Hash password with bcrypt and store it as a string
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user_data = {
            'email': email,
            'password_hash': password_hash.decode('utf-8'),  # Store as string in MongoDB
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
    def get_by_id(user_id):
        """Get user by ID"""
        try:
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            return User(user_data) if user_data else None
        except:
            return None
    
    def check_password(self, password):
        """Check if password is correct"""
        if not self.password_hash:
            return False
        try:
            # Convert stored hash string back to bytes for comparison
            stored_hash = self.password_hash.encode('utf-8')
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
        except Exception:
            return False
    
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