import os
from job_app_tracker import create_app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 3000))
    
    # Run the app
    app.run(
        host='localhost',
        port=port
    ) 