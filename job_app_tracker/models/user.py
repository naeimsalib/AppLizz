from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from job_app_tracker.config.mongodb import mongo
from bson import ObjectId
from datetime import datetime

class User(UserMixin):
    def __init__(self, user_data):
        self._id = user_data.get('_id')
        self.email = user_data.get('email')
        self.username = user_data.get('username')
        self.password_hash = user_data.get('password_hash')
        self.first_name = user_data.get('first_name')
        self.last_name = user_data.get('last_name')
        self.created_at = user_data.get('created_at', datetime.now())
        self._is_active = user_data.get('is_active', True)

        # Subscription info
        self.is_premium = user_data.get('is_premium', False)
        self.subscription = user_data.get('subscription', {})

    @property
    def id(self):
        """Return string representation of _id for Flask-Login"""
        return str(self._id) if self._id else None

    @property
    def is_active(self):
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        self._is_active = value
        # Update in database
        if hasattr(self, '_id') and self._id:
            mongo.db.users.update_one(
                {"_id": ObjectId(self._id)},
                {"$set": {"is_active": value}}
            )

    def get_id(self):
        return str(self._id)

    @staticmethod
    def create_user(username, email, password, first_name=None, last_name=None):
        """Create a new user"""
        # Check if username already exists
        if mongo.db.users.find_one({"username": username}):
            return False, "Username already exists"
        
        # Check if email already exists
        if mongo.db.users.find_one({"email": email}):
            return False, "Email already exists"
        
        # Create user document
        user_data = {
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "created_at": datetime.now(),
            "is_active": True,
            "is_premium": False,
            "subscription": {
                "plan": "free",
                "start_date": None,
                "end_date": None,
                "payment_id": None
            }
        }
        
        # Insert into database
        result = mongo.db.users.insert_one(user_data)
        
        if result.inserted_id:
            user_data['_id'] = result.inserted_id
            return True, User(user_data)
        
        return False, "Failed to create user"
    
    @staticmethod
    def get_by_id(user_id):
        """Find user by ID"""
        if not user_id:
            return None
        try:
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            return User(user_data) if user_data else None
        except:
            return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        user_data = mongo.db.users.find_one({"username": username})
        if user_data:
            return User(user_data)
        return None
    
    @staticmethod
    def get_by_email(email):
        """Find user by email (case-insensitive)"""
        if not email:
            return None
        user_data = mongo.db.users.find_one(
            {'email': email.lower()},
            collation={'locale': 'en', 'strength': 2}
        )
        return User(user_data) if user_data else None
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def update_password(self, new_password):
        """Update password"""
        password_hash = generate_password_hash(new_password)
        mongo.db.users.update_one(
            {"_id": ObjectId(self._id)},
            {"$set": {"password_hash": password_hash}}
        )
        self.password_hash = password_hash
        return True
    
    def update_profile(self, first_name=None, last_name=None, email=None):
        """Update user profile"""
        updates = {}
        if first_name is not None:
            updates["first_name"] = first_name
        if last_name is not None:
            updates["last_name"] = last_name
        if email is not None:
            # Check if email already exists
            if email != self.email and mongo.db.users.find_one({"email": email}):
                return False, "Email already exists"
            updates["email"] = email
        
        if updates:
            mongo.db.users.update_one(
                {"_id": ObjectId(self._id)},
                {"$set": updates}
            )
            
            # Update instance attributes
            for key, value in updates.items():
                setattr(self, key, value)
            
            return True, "Profile updated successfully"
        
        return False, "No updates provided"
    
    def update_subscription(self, is_premium=None, plan=None, 
                           start_date=None, end_date=None, payment_id=None):
        """Update subscription"""
        updates = {}
        subscription_updates = {}
        
        if is_premium is not None:
            updates["is_premium"] = is_premium
        
        if plan is not None:
            subscription_updates["plan"] = plan
        
        if start_date is not None:
            subscription_updates["start_date"] = start_date
        
        if end_date is not None:
            subscription_updates["end_date"] = end_date
        
        if payment_id is not None:
            subscription_updates["payment_id"] = payment_id
        
        if subscription_updates:
            updates["subscription"] = subscription_updates
        
        if updates:
            mongo.db.users.update_one(
                {"_id": ObjectId(self._id)},
                {"$set": updates}
            )
            
            # Update instance attributes
            if "is_premium" in updates:
                self.is_premium = updates["is_premium"]
            
            if "subscription" in updates:
                if not hasattr(self, "subscription"):
                    self.subscription = {}
                
                for key, value in subscription_updates.items():
                    self.subscription[key] = value
            
            return True
        
        return False
    
    def save(self):
        """Save or update user"""
        user_data = {
            'email': self.email.lower(),  # Store email in lowercase
            'username': self.username,
            'password_hash': self.password_hash,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self._is_active,
            'is_premium': self.is_premium,
            'subscription': self.subscription
        }
        
        if self._id:
            mongo.db.users.update_one(
                {'_id': self._id},
                {'$set': user_data}
            )
        else:
            result = mongo.db.users.insert_one(user_data)
            self._id = result.inserted_id
        return True
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "id": self._id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "created_at": self.created_at,
            "is_active": self._is_active,
            "is_premium": self.is_premium,
            "subscription": self.subscription
        } 