"""
Telegram Quiz Bot - Main entry point
This file provides both the bot entry point and the Flask web app
"""
import os
import logging
from simple_bot import main as start_bot
from app import app  # Import Flask app for the web interface

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create necessary data directories if they don't exist
os.makedirs('data', exist_ok=True)

def main():
    """Start the bot"""
    logger.info("Starting Telegram Quiz Bot")
    start_bot()

if __name__ == '__main__':
    main()
