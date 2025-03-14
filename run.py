from job_app_tracker import create_app
import argparse
import cProfile
import pstats
import io
import logging

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the JobJourney application')
    parser.add_argument('--port', type=int, default=3000, help='Port to run the application on')
    parser.add_argument('--no-debug', action='store_true', help='Run without debug mode for better performance')
    parser.add_argument('--local', action='store_true', help='Run only on localhost (127.0.0.1) instead of all interfaces')
    parser.add_argument('--profile', action='store_true', help='Run with profiling to diagnose performance issues')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        default='INFO', help='Set the logging level')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    debug_mode = not args.no_debug
    host = '127.0.0.1' if args.local else '0.0.0.0'
    
    if args.profile:
        # Run with profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        app.run(host=host, port=args.port, debug=debug_mode)
        
        profiler.disable()
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(30)  # Print top 30 time-consuming functions
        print(s.getvalue())
    else:
        # Normal run
        app.run(host=host, port=args.port, debug=debug_mode) 