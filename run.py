import os
from job_app_tracker import create_app
import logging
from logging.config import dictConfig

# Configure logging
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/applizz.log',
            'maxBytes': 10240000,
            'backupCount': 10,
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi', 'file']
    }
})

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 3000))
    
    # Run the app
    if os.environ.get('FLASK_ENV') == 'production':
        # Production settings
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    else:
        # Development settings
        app.run(
            host='localhost',
            port=port,
            debug=True,
            use_reloader=True
        ) 