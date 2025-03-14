import os
from flask import Flask
from flask_login import LoginManager
from .config.mongodb import init_mongodb
from .models.user import User
from dotenv import load_dotenv

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
    app = Flask(__name__)
    app.config.from_object('job_app_tracker.config.default')
    
    if config:
        app.config.update(config)
    
    # Initialize MongoDB
    init_mongodb(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    # Register blueprints
    from .main.routes import main
    from .auth.routes import auth
    from .routes.email_routes import email_bp
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(email_bp, url_prefix='/email')
    
    return app 