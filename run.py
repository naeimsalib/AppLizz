import os
from dotenv import load_dotenv
from job_app_tracker import create_app

# Load environment variables
load_dotenv(override=True)

# Create the application
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 3000))
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    ) 