import os
from dotenv import load_dotenv
from job_app_tracker import create_app

# Create the Flask app
app = create_app()

if __name__ == '__main__':
    # Fetch port from environment variable or use 3000 as default
    port = int(os.environ.get('PORT', 3000))
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    ) 
