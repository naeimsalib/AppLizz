from job_app_tracker import create_app
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Determine if we're running in production or development
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        # Production settings: no debug, bind to all interfaces
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)), debug=False)
    else:
        # Development settings
        app.run(host='0.0.0.0', port=3000, debug=True) 