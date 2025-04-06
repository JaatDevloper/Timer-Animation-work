"""
Telegram bot implementation for the Quiz Bot application
Handles bot initialization and command routing
"""
import os
import logging
import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, ContextTypes
)
from config import TOKEN
import quiz_handler
import user_handler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
SELECTING_QUIZ, ANSWERING = range(2)
# States for quiz creation
QUESTION, OPTIONS, ANSWER, CATEGORY = range(3, 7)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for the /start command
    Introduces the bot and displays the main menu
    """
    user = update.effective_user
    await update.message.reply_text(
        f"Hello, {user.first_name}! I'm the Quiz Bot.\n\n"
        f"I can help you test your knowledge with various quizzes.\n\n"
        f"Use /quiz to start a quiz\n"
        f"Use /stats to see your performance\n"
        f"Use /help for more information"
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /help command
    Displays available commands and bot usage information
    """
    help_text = (
        "📚 *Available Commands* 📚\n\n"
        "/start - Start the bot\n"
        "/quiz - Start a new quiz\n"
        "/stats - View your quiz statistics\n"
        "/help - Show this help message\n"
        "/add_quiz - Create a new quiz question\n\n"
        "*How to use the Quiz Bot:*\n"
        "1. Use /quiz to start a new quiz session\n"
        "2. Answer the questions by selecting one of the options\n"
        "3. After completing the quiz, view your score\n"
        "4. Check your overall statistics with /stats\n"
        "5. Create your own quiz questions with /add_quiz"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /stats command
    Shows the user's quiz statistics
    """
    user_id = str(update.effective_user.id)
    stats_text = user_handler.get_user_stats(user_id)
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for the /quiz command
    Starts a new quiz session
    """
    return await quiz_handler.start_quiz(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for button callbacks from inline keyboards
    Routes to appropriate handlers based on callback data
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('answer_'):
        return await quiz_handler.handle_answer(update, context)
    else:
        await query.edit_message_text(f"Unrecognized button: {data}")
        return ConversationHandler.END

def setup_bot() -> Application:
    """
    Sets up and configures the bot application
    Returns the Application instance
    """
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    
    # Add a callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add conversation handler for adding quizzes
    add_quiz_handler = ConversationHandler(
        entry_points=[CommandHandler("add_quiz", add_quiz_command)],
        states={
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_question)],
            OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_options)],
            ANSWER: [CallbackQueryHandler(get_answer, pattern=r'^option_\d+$')],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: None)]  # Placeholder
        },
        fallbacks=[CommandHandler("cancel", cancel_quiz_creation)]
    )
    application.add_handler(add_quiz_handler)
    
    return application

async def add_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Command to start adding a new quiz question"""
    await update.message.reply_text(
        "Let's create a new quiz question!\n\n"
        "Please send me the question text.\n"
        "For example: 'What is the capital of France?'\n\n"
        "Send /cancel at any time to abort the process."
    )
    return QUESTION

async def get_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receiving the question text"""
    question_text = update.message.text
    context.user_data['question'] = question_text
    
    await update.message.reply_text(
        "Great! Now send me the answer options, one per line.\n"
        "For example:\n"
        "Paris\n"
        "London\n"
        "Berlin\n"
        "Madrid\n\n"
        "Send /cancel to abort."
    )
    return OPTIONS

async def get_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receiving the answer options"""
    options_text = update.message.text
    options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
    
    if len(options) < 2:
        await update.message.reply_text(
            "You need to provide at least 2 options. Please try again."
        )
        return OPTIONS
    
    context.user_data['options'] = options
    
    # Build keyboard for selecting correct answer
    keyboard = []
    for i, option in enumerate(options):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"option_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Now select which option is the correct answer:",
        reply_markup=reply_markup
    )
    return ANSWER

async def get_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receiving the correct answer"""
    query = update.callback_query
    await query.answer()
    
    # Extract the answer index
    answer_idx = int(query.data.split('_')[1])
    
    # Get the stored question data
    question = context.user_data.get('question')
    options = context.user_data.get('options')
    
    if not question or not options:
        await query.edit_message_text("Error: Missing question data.")
        return ConversationHandler.END
    
    # Create and save the new question
    new_question = {
        'question': question,
        'options': options,
        'answer': answer_idx,
        'category': 'User Created'
    }
    
    questions = quiz_handler.load_questions()
    questions.append(new_question)
    quiz_handler.save_questions(questions)
    
    await query.edit_message_text(
        f"✅ Quiz question created successfully!\n\n"
        f"Question: {question}\n\n"
        f"Options:\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options)) + "\n\n"
        f"Correct answer: {options[answer_idx]}\n\n"
        f"Use /quiz to test it out!"
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_quiz_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the quiz creation process"""
    await update.message.reply_text(
        "Quiz creation cancelled. Use /help to see available commands."
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    """Start the bot"""
    # Create the data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Set up and start the bot application
    application = setup_bot()
    application.run_polling()

if __name__ == '__main__':
    main()
