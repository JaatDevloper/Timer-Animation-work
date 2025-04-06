"""
Configuration settings for the Telegram Quiz Bot
"""
import os

# Bot configuration
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')  # Telegram bot token from environment variable

# Quiz configuration
QUESTIONS_PER_QUIZ = 5  # Number of questions per quiz session
OPTIONS_PER_QUESTION = 4  # Number of options per question
QUIZ_TIMEOUT = 30  # Time in seconds allowed for answering each question

# File paths
QUESTIONS_FILE = 'data/questions.json'  # Path to questions data file
USERS_FILE = 'data/users.json'  # Path to user data file

# Make sure the bot token is available
if not TOKEN:
    raise ValueError("Telegram bot token not found! Set the TELEGRAM_BOT_TOKEN environment variable.")
