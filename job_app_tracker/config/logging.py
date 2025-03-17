import logging
import os
from pathlib import Path

# Create logs directory if it doesn't exist
Path('logs').mkdir(parents=True, exist_ok=True)
Path('logs/analysis').mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/email_scan.log'),
        logging.StreamHandler()
    ]
)

# Create logger
logger = logging.getLogger('email_service')
logger.setLevel(logging.INFO)

# Create handlers
file_handler = logging.FileHandler('logs/email_scan.log')
console_handler = logging.StreamHandler()

# Create formatters and add it to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Export logger
__all__ = ['logger'] 