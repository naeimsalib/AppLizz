from flask import Flask, request
from flask_login import LoginManager
import os
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
import logging
from logging.handlers import RotatingFileHandler

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
csrf = CSRFProtect()

def setup_logging(app):
    """Configure logging for the application"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    
    file_handler = RotatingFileHandler(
        'logs/applizz.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Applizz startup')

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Load the default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
        MONGODB_URI=os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/job_app_tracker'),
        UPLOAD_FOLDER=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16 MB max upload
    )
    
    # Load production configuration if FLASK_ENV is production
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object('job_app_tracker.config.production')
    
    # Initialize the upload folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Initialize MongoDB with connection pooling
    from job_app_tracker.config.mongodb import init_db
    init_db(app)
    
    # Initialize extensions
    login_manager.init_app(app)
    csrf.init_app(app)
    CORS(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    from job_app_tracker.auth.routes import auth_bp
    from job_app_tracker.main.routes import main
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main, url_prefix='')
    
    # User loader for Flask-Login
    from job_app_tracker.models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        app.logger.warning(f'Page not found: {request.url}')
        return "Page not found (404)", 404
    
    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f'Server Error: {str(e)}')
        return "Internal server error (500)", 500
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers to response"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        if app.config.get('STRICT_TRANSPORT_SECURITY'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    return app 