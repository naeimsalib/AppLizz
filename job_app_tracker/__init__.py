import os
from flask import Flask, request
from flask_login import LoginManager
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from .config.mongodb import init_mongodb, mongo
from .models.user import User
from dotenv import load_dotenv
import logging
from bson.objectid import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables in development
if os.environ.get('FLASK_ENV') != 'production':
    load_dotenv()

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
csrf = CSRFProtect()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure app
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'default-secret-key'),
        MONGODB_URI=os.environ.get('MONGODB_URI'),
        UPLOAD_FOLDER=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16 MB max upload
        DEBUG=os.environ.get('FLASK_ENV') != 'production'
    )
    
    # Log configuration
    logging.info(f"MongoDB URI: {app.config['MONGODB_URI']}")
    
    # Initialize the upload folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Initialize MongoDB with connection pooling
    init_mongodb(app)
    
    # Initialize extensions
    login_manager.init_app(app)
    csrf.init_app(app)
    CORS(app)
    
    # Register blueprints
    from .main.routes import main
    from .auth.routes import auth
    from .application.routes import application
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(application)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        return User(data) if data else None
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return "Page not found (404)", 404
    
    @app.errorhandler(500)
    def server_error(e):
        return "Internal server error (500)", 500
    
    return app 