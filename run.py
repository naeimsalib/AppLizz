from job_app_tracker import create_app
import argparse

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the JobJourney application')
    parser.add_argument('--port', type=int, default=3000, help='Port to run the application on')
    parser.add_argument('--no-debug', action='store_true', help='Run without debug mode for better performance')
    parser.add_argument('--local', action='store_true', help='Run only on localhost (127.0.0.1) instead of all interfaces')
    args = parser.parse_args()
    
    debug_mode = not args.no_debug
    host = '127.0.0.1' if args.local else '0.0.0.0'
    
    app.run(host=host, port=args.port, debug=debug_mode) 