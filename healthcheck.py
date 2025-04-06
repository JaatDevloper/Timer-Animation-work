"""
Health check script for Telegram Quiz Bot
Used by containers to verify the app is running properly
"""
import os
import sys
import logging
import requests
import socket
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_web_server():
    """Check if the web server is running"""
    try:
        # Get the host and port
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        
        # If we're using 0.0.0.0, change to localhost for checking
        check_host = 'localhost' if host == '0.0.0.0' else host
        
        # Try to connect to the web server
        url = f"http://{check_host}:{port}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            logger.info(f"Web server is running: {url}")
            return True
        else:
            logger.error(f"Web server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Web server check failed: {e}")
        return False

def check_bot_token():
    """Check if the Telegram bot token is set"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
        return False
    
    logger.info("TELEGRAM_BOT_TOKEN is set")
    return True

def check_data_directory():
    """Check if the data directory exists and is writable"""
    data_dir = 'data'
    if not os.path.exists(data_dir):
        logger.error(f"Data directory '{data_dir}' does not exist")
        return False
    
    if not os.access(data_dir, os.W_OK):
        logger.error(f"Data directory '{data_dir}' is not writable")
        return False
    
    logger.info(f"Data directory '{data_dir}' exists and is writable")
    return True

def main():
    """Run health checks and return status code"""
    checks = [
        check_web_server,
        check_bot_token,
        check_data_directory
    ]
    
    # Run all checks
    results = [check() for check in checks]
    
    # Return 0 if all checks pass, 1 otherwise
    if all(results):
        logger.info("All health checks passed")
        return 0
    else:
        logger.error("Some health checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
