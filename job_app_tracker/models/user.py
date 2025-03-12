from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from job_app_tracker.config.mongodb import mongo
from bson.objectid import ObjectId

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id', ''))
        self.email = user_data.get('email')
        self.password_hash = user_data.get('password_hash')
        self.name = user_data.get('name')
        
    @staticmethod
    def create_user(email, password, name):
        """Create a new user"""
        user_data = {
            'email': email,
            'password_hash': generate_password_hash(password),
            'name': name
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
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name
        } 