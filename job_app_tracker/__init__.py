from flask import Flask
from flask_login import LoginManager
import os
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
csrf = CSRFProtect()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure the app
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
        MONGODB_URI=os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/job_app_tracker'),
        UPLOAD_FOLDER=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16 MB max upload
    )
    
    # Initialize the upload folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Initialize MongoDB
    from job_app_tracker.config.mongodb import init_db
    init_db(app)
    
    # Initialize extensions
    login_manager.init_app(app)
    csrf.init_app(app)
    CORS(app)
    
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
        return "Page not found (404)", 404
    
    @app.errorhandler(500)
    def server_error(e):
        return "Internal server error (500)", 500
    
    return app 