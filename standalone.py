"""
Standalone runner for Telegram Quiz Bot
This script runs both the Flask web app and the Telegram bot in a single process
"""
import os
import sys
import time
import logging
import threading
import signal
import atexit
from flask import Flask, jsonify
from main import app
from simple_bot import main as start_bot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flag to track if the bot thread is running
bot_thread_running = False
bot_thread = None

def run_bot():
    """Run the Telegram bot in a separate thread"""
    global bot_thread_running
    try:
        logger.info("Starting Telegram bot...")
        bot_thread_running = True
        start_bot()
    except Exception as e:
        logger.error(f"Error in bot thread: {e}")
    finally:
        bot_thread_running = False
        logger.info("Bot thread has stopped")

# Add a health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    status = {
        'status': 'ok',
        'web_server': True,
        'bot_running': bot_thread_running,
        'timestamp': time.time()
    }
    return jsonify(status)

def cleanup():
    """Cleanup function to run when the application exits"""
    logger.info("Shutting down the application...")
    if bot_thread and bot_thread.is_alive():
        logger.info("Waiting for bot thread to terminate...")
        bot_thread.join(timeout=5)
        if bot_thread.is_alive():
            logger.warning("Bot thread did not terminate gracefully")

def signal_handler(sig, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {sig}")
    cleanup()
    sys.exit(0)

def main():
    """Main function to run both the web server and the bot"""
    global bot_thread
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Register cleanup functions
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get the port from environment variable
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Start the Flask web server
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port)

if __name__ == '__main__':
    main()
