"""
Configuration settings for the Telegram Quiz Bot
"""
import os

# Bot configuration
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8131829458:AAEC4jLUZFYnm7k9KOOAkP_D-XwhxgB5nGQ')  # Telegram bot token from environment variable
API_ID = os.getenv('API_ID', '28624690')  # Telegram API ID for Pyrogram
API_HASH = os.getenv('API_HASH', '67e6593b5a9b5ab20b11ccef6700af5b')  # Telegram API Hash for Pyrogram
OWNER_ID = os.getenv('OWNER_ID', '897155563')  # Telegram User ID of the bot owner

# Database configuration
MONGODB_URL = os.getenv('MONGODB_URL', '')  # MongoDB connection URL

# Channel configuration
FORCESUB_CHANNEL = os.getenv('FORCESUB_CHANNEL', 'https://t.me/IMJaatCoderX')  # Channel username for force subscription

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

# Validate Pyrogram credentials if using Pyrogram features
if (API_ID or API_HASH) and not (API_ID and API_HASH):
    raise ValueError("Both API_ID and API_HASH must be provided for Pyrogram features.")

# Validate MongoDB URL if using MongoDB
if MONGODB_URL:
    # Placeholder for MongoDB validation logic
    pass
