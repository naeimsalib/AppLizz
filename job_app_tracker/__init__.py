import os
from flask import Flask, request
from flask_login import LoginManager
from flask_cors import CORS
from .config.mongodb import init_mongodb
from .models.user import User
from dotenv import load_dotenv
from .config.default import Config

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
    
    # Load configuration
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    
    # Initialize CORS with configuration
    CORS(app, resources={r"/*": {"origins": app.config['CORS_ORIGINS']}})
    
    # Initialize MongoDB
    init_mongodb(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    # Add security headers to all responses
    @app.after_request
    def add_security_headers(response):
        for header, value in app.config['SECURITY_HEADERS'].items():
            response.headers[header] = value
        return response
    
    # Register blueprints
    from .main.routes import main
    from .auth.routes import auth
    from .routes.email_routes import email_bp
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(email_bp, url_prefix='/email')
    
    # Start scheduled tasks
    with app.app_context():
        # Schedule cache cleanup
        from .services.email_service import EmailService
        EmailService.schedule_cache_cleanup()
    
    return app 