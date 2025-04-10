from flask_login import UserMixin
import bcrypt
from job_app_tracker.config.mongodb import mongo
from bson import ObjectId
from datetime import datetime

class User(UserMixin):
    def __init__(self, data):
        if data is None:
            return None
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

    @classmethod
    def create_user(cls, email, password, name):
        """Create a new user with proper password hashing"""
        try:
            # Convert email to lowercase
            email = email.lower()
            
            # Generate salt and hash password
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password_bytes, salt)
            
            # Store hash as bytes in MongoDB
            user_data = {
                'email': email,
                'password_hash': password_hash,
                'name': name,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'email_connected': False,
                'email_settings': {}
            }
            
            # Insert the user
            result = mongo.db.users.insert_one(user_data)
            user_data['_id'] = result.inserted_id
            
            return cls(user_data)
        except Exception as e:
            print(f"User creation error: {str(e)}")
            return None

    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        """Check if password is correct"""
        if not self.password_hash:
            return False
        try:
            # Make sure password_hash is in bytes
            stored_hash = self.password_hash.encode('utf-8') if isinstance(self.password_hash, str) else self.password_hash
            # Convert input password to bytes
            password_bytes = password.encode('utf-8')
            # Verify password
            return bcrypt.checkpw(password_bytes, stored_hash)
        except Exception as e:
            print(f"Password verification error: {str(e)}")
            return False
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        try:
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            return User(user_data) if user_data else None
        except:
            return None
    
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