import os
from job_app_tracker import create_app

# Create the Flask app
app = create_app()

if __name__ == '__main__':
    # Fetch port from environment variable or use 3000 as default
    port = int(os.environ.get('PORT', 3000))

    # Run the app in production mode
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True
    )
