import os
from dotenv import load_dotenv
from job_app_tracker import create_app

# Load environment variables
load_dotenv()

# Create the Flask app
app = create_app()

if __name__ == '__main__':
    # Fetch port from environment variable or use 5000 as default
    port = int(os.environ.get('PORT', 5000))
    
    # Set debug mode based on environment
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    ) 
