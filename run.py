import os
from dotenv import load_dotenv
from job_app_tracker import create_app

<<<<<<< HEAD
# Create the Flask app
=======
# Load environment variables
load_dotenv(override=True)

# Create the application
>>>>>>> 99d1cdd50f1d2381023d99cc522bc43f5b53b4d4
app = create_app()

if __name__ == '__main__':
    # Fetch port from environment variable or use 3000 as default
    port = int(os.environ.get('PORT', 3000))
<<<<<<< HEAD

    # Run the app in production mode
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True
    )
=======
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    ) 
>>>>>>> 99d1cdd50f1d2381023d99cc522bc43f5b53b4d4
