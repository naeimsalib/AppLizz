from job_app_tracker import create_app
import argparse

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the JobJourney application')
    parser.add_argument('--port', type=int, default=3000, help='Port to run the application on')
    args = parser.parse_args()
    
    app.run(host='0.0.0.0', port=args.port, debug=True) 