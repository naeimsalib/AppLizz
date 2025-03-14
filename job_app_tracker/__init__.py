import os
from flask import Flask
from flask_login import LoginManager
from .config.mongodb import init_mongodb
from .models.user import User
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

def create_app(config=None):
    logger.info("Starting application initialization")
    start_time = __import__('time').time()
    
    app = Flask(__name__)
    app.config.from_object('job_app_tracker.config.default')
    
    if config:
        app.config.update(config)
    
    # Initialize MongoDB
    logger.info("Initializing MongoDB connection")
    init_mongodb(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    # Register blueprints - lazy loading to improve startup time
    logger.info("Registering blueprints")
    with app.app_context():
        from .main.routes import main
        from .auth.routes import auth
        from .routes.email_routes import email_bp
        
        app.register_blueprint(main)
        app.register_blueprint(auth, url_prefix='/auth')
        app.register_blueprint(email_bp, url_prefix='/email')
    
    end_time = __import__('time').time()
    logger.info(f"Application initialized in {end_time - start_time:.2f} seconds")
    
    return app 