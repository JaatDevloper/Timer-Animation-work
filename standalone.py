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
import asyncio
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
bot_loop = None

def run_bot():
    """Run the Telegram bot in a separate thread with its own event loop"""
    global bot_thread_running, bot_loop
    try:
        logger.info("Starting Telegram bot...")
        bot_thread_running = True
        
        # Create a new event loop for this thread
        bot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(bot_loop)
        
        # Run the bot using the new event loop
        bot_loop.run_until_complete(start_bot_async())
        
    except Exception as e:
        logger.error(f"Error in bot thread: {e}")
    finally:
        bot_thread_running = False
        logger.info("Bot thread has stopped")

async def start_bot_async():
    """Async wrapper for the bot's main function"""
    # Import the necessary parts to run the bot
    from telegram.ext import Application
    from config import TOKEN
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Import and setup handlers from simple_bot
    from simple_bot import (
        start, help_command, stats_command, play, handle_poll_answer, 
        add_quiz, get_question, get_options, get_answer, cancel,
        list_quizzes, clone_quiz, edit_quiz, save_forward, remove_quiz,
        button_callback, QUESTION, OPTIONS, ANSWER, CLONE_URL, EDIT_SELECT,
        EDIT_QUESTION, EDIT_OPTIONS, EDIT_ANSWER
    )
    from telegram.ext import (
        CommandHandler, PollHandler, CallbackQueryHandler,
        ConversationHandler, MessageHandler, filters
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CommandHandler("list", list_quizzes))
    application.add_handler(CommandHandler("remove", remove_quiz))
    
    # Handle poll answers
    application.add_handler(PollHandler(handle_poll_answer))
    
    # Add conversation handler for quiz creation
    add_quiz_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_quiz)],
        states={
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_question)],
            OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_options)],
            ANSWER: [CallbackQueryHandler(get_answer, pattern=r"^answer_")]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    application.add_handler(add_quiz_conv)
    
    # Add conversation handler for quiz cloning
    clone_quiz_conv = ConversationHandler(
        entry_points=[CommandHandler("clone", clone_quiz)],
        states={
            CLONE_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, clone_quiz)],
            ANSWER: [CallbackQueryHandler(get_answer, pattern=r"^answer_")]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    application.add_handler(clone_quiz_conv)
    
    # Add conversation handler for quiz editing
    edit_quiz_conv = ConversationHandler(
        entry_points=[CommandHandler("edit", edit_quiz)],
        states={
            EDIT_SELECT: [CallbackQueryHandler(lambda u, c: None, pattern=r"^edit_")],
            EDIT_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: None)],
            EDIT_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: None)],
            EDIT_ANSWER: [CallbackQueryHandler(lambda u, c: None, pattern=r"^editanswer_")]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    application.add_handler(edit_quiz_conv)
    
    # Add handler for saving forwarded quizzes
    application.add_handler(CommandHandler("saveforward", save_forward))
    
    # Add callback query handler for button callbacks
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the Bot using polling (no webhook)
    await application.initialize()
    await application.start_polling(allowed_updates=["message", "callback_query", "poll", "poll_answer"])
    await application.updater.start_polling()
    
    try:
        # Keep the bot running until a shutdown signal is received
        logger.info("Bot is running. Press Ctrl+C to stop")
        await application.updater.stop()
    finally:
        await application.stop()

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
    global bot_loop
    if bot_thread and bot_thread.is_alive():
        logger.info("Waiting for bot thread to terminate...")
        if bot_loop and bot_loop.is_running():
            # Schedule task to stop the loop
            asyncio.run_coroutine_threadsafe(
                asyncio.sleep(0.1),  # A small sleep to allow the task to be scheduled
                bot_loop
            ).result(timeout=5)
            bot_loop.stop()
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
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Start the Flask web server
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port)

if __name__ == '__main__':
    main()
