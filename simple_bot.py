"""
Simple Telegram Quiz Bot implementation
"""
import os
import json
import random
import logging
import re
import requests
from urllib.parse import urlparse
from telegram import Update, Poll, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, PollHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
QUESTION, OPTIONS, ANSWER = range(3)
EDIT_SELECT, EDIT_QUESTION, EDIT_OPTIONS, EDIT_ANSWER = range(3, 7)
CLONE_URL, CLONE_MANUAL = range(7, 9)

# Get bot token from environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# File paths
QUESTIONS_FILE = 'data/questions.json'
USERS_FILE = 'data/users.json'

def load_questions():
    """Load questions from the JSON file"""
    try:
        if os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as file:
                questions = json.load(file)
            logger.info(f"Loaded {len(questions)} questions")
            return questions
        else:
            # Create sample questions if file doesn't exist
            questions = [
                {
                    "id": 1,
                    "question": "What is the capital of France?",
                    "options": ["Berlin", "Madrid", "Paris", "Rome"],
                    "answer": 2,  # Paris (0-based index)
                    "category": "Geography"
                },
                {
                    "id": 2,
                    "question": "Which planet is known as the Red Planet?",
                    "options": ["Venus", "Mars", "Jupiter", "Saturn"],
                    "answer": 1,  # Mars (0-based index)
                    "category": "Science"
                }
            ]
            save_questions(questions)
            return questions
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        return []

def save_questions(questions):
    """Save questions to the JSON file"""
    try:
        with open(QUESTIONS_FILE, 'w', encoding='utf-8') as file:
            json.dump(questions, file, ensure_ascii=False, indent=4)
        logger.info(f"Saved {len(questions)} questions")
        return True
    except Exception as e:
        logger.error(f"Error saving questions: {e}")
        return False

def get_next_question_id():
    """Get the next available question ID"""
    questions = load_questions()
    if not questions:
        return 1
    return max(q.get("id", 0) for q in questions) + 1

def get_question_by_id(question_id):
    """Get a question by its ID"""
    questions = load_questions()
    for question in questions:
        if question.get("id") == question_id:
            return question
    return None

def delete_question_by_id(question_id):
    """Delete a question by its ID"""
    questions = load_questions()
    updated_questions = [q for q in questions if q.get("id") != question_id]
    if len(updated_questions) < len(questions):
        save_questions(updated_questions)
        return True
    return False

def parse_telegram_quiz_url(url):
    """Parse a Telegram quiz URL to extract question and options"""
    try:
        # Extract question and options from URL parameters
        parsed_url = urlparse(url)
        if not parsed_url.netloc or "t.me" not in parsed_url.netloc:
            return None
        
        # Try to fetch the webpage content for extracting quiz details
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
            
        content = response.text
        
        # Extract quiz title using meta tags or OpenGraph data
        title_match = re.search(r'<meta property="og:title" content="([^"]+)"', content)
        title_match2 = re.search(r'<meta property="twitter:title" content="([^"]+)"', content)
        description_match = re.search(r'<meta property="og:description" content="([^"]+)"', content)
        
        # Extract quiz details from the page
        quiz_title = None
        quiz_description = None
        
        if title_match:
            quiz_title = title_match.group(1).strip()
        elif title_match2:
            quiz_title = title_match2.group(1).strip()
            
        if description_match:
            quiz_description = description_match.group(1).strip()
        
        # Try to extract quiz information from page content
        # Look for the text that might contain the question
        question = None
        if quiz_title and "Quiz" in quiz_title:
            # Try to extract the actual question from the description
            if quiz_description:
                question = quiz_description
            else:
                question = quiz_title
        elif quiz_description:
            question = quiz_description
        
        # If we still don't have a question, look for it in the page content
        if not question:
            # Try to find question in HTML content
            question_container = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', content, re.DOTALL)
            if question_container:
                # Clean up HTML tags to get plain text
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(question_container.group(1), 'html.parser')
                question = soup.get_text().strip()
        
        # Extract options from the page content
        options = []
        options_matches = re.findall(r'<div class="tgme_widget_message_poll_option_text">([^<]+)</div>', content)
        if options_matches:
            options = [opt.strip() for opt in options_matches]
        
        # If we couldn't find options through typical methods, try a more general approach
        if not options:
            # Look for any structured data that might contain options
            option_containers = re.findall(r'<div class="[^"]*option[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)
            if option_containers:
                from bs4 import BeautifulSoup
                for container in option_containers:
                    soup = BeautifulSoup(container, 'html.parser')
                    option_text = soup.get_text().strip()
                    if option_text and len(option_text) < 100:  # Reasonable length for an option
                        options.append(option_text)
        
        # Some quizzes might have the question and options embedded in a script tag
        if not question or not options:
            script_data = re.search(r'<script[^>]*>.*?({.*?})</script>', content, re.DOTALL)
            if script_data:
                try:
                    import json
                    # Try to extract JSON data
                    json_str = script_data.group(1)
                    # Find valid JSON object within the script
                    json_match = re.search(r'{.*}', json_str)
                    if json_match:
                        json_data = json.loads(json_match.group(0))
                        # Look for quiz data in JSON
                        if 'question' in json_data:
                            question = json_data['question']
                        if 'options' in json_data and isinstance(json_data['options'], list):
                            options = json_data['options']
                except Exception as e:
                    logger.debug(f"Failed to parse JSON from script tag: {e}")
        
        # If we found a question and at least 2 options, create and return the quiz data
        if question and options and len(options) >= 2:
            logger.info(f"Successfully extracted quiz: {question} with {len(options)} options")
            return {
                "question": question,
                "options": options,
                "answer": 0  # Default to first option, user needs to set the correct answer
            }
        else:
            logger.error(f"Failed to extract complete quiz data. Question: {question}, Options count: {len(options) if options else 0}")
            
    except Exception as e:
        logger.error(f"Error parsing Telegram quiz URL: {e}")
    
    logger.warning(f"Could not parse quiz from URL: {url}")
    return None

def load_users():
    """Load users from the JSON file"""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        return {}
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return {}

def save_user_data(user_data):
    """Save user data to the JSON file"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as file:
            json.dump(user_data, file, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving user data: {e}")
        return False

def update_user_stats(user_id, user_name, is_correct):
    """Update user statistics"""
    user_data = load_users()
    
    # Convert user_id to string for JSON compatibility
    user_id = str(user_id)
    
    if user_id not in user_data:
        user_data[user_id] = {
            "name": user_name,
            "correct": 0,
            "total": 0
        }
    
    user_data[user_id]["total"] += 1
    if is_correct:
        user_data[user_id]["correct"] += 1
    
    return save_user_data(user_data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello, {user.first_name}! I'm the Quiz Bot 🎯\n\n"
        f"I can help you play and create quiz questions.\n\n"
        f"Use /play to start a quiz\n"
        f"Use /add to create a new quiz question\n"
        f"Use /help to see all available commands"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /help command"""
    help_text = (
        "📚 *Available Commands* 📚\n\n"
        "/start - Start the bot\n"
        "/play - Play a random quiz\n"
        "/stats - View your quiz statistics\n"
        "/add - Create a new quiz question\n"
        "/list - List all available quizzes\n"
        "/clone - Clone a quiz from a Telegram link\n"
        "/edit - Edit an existing quiz\n"
        "/remove - Delete a quiz question\n"
        "/saveforward - Save a forwarded quiz\n"
        "/cancel - Cancel current operation\n"
        "/help - Show this help message\n\n"
        "To save a quiz someone sent you, forward it to me and I'll ask if you want to save it!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /stats command"""
    user = update.effective_user
    user_data = load_users()
    user_id = str(user.id)
    
    if user_id in user_data:
        stats = user_data[user_id]
        accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        
        await update.message.reply_text(
            f"📊 *Your Quiz Statistics* 📊\n\n"
            f"Total questions answered: {stats['total']}\n"
            f"Correct answers: {stats['correct']}\n"
            f"Accuracy: {accuracy:.1f}%",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "You haven't answered any quiz questions yet. Use /play to start a quiz!"
        )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /play command - starts a quiz"""
    questions = load_questions()
    
    if not questions:
        await update.message.reply_text(
            "No quiz questions available. Use /add to create some!"
        )
        return
    
    # Select a random question
    question_data = random.choice(questions)
    question = question_data["question"]
    options = question_data["options"]
    correct_option_id = question_data["answer"]
    
    # Store the correct answer in user_data for checking later
    context.user_data["quiz_correct_answer"] = correct_option_id
    context.user_data["quiz_question_id"] = question_data.get("id")
    
    # Send the quiz as a poll
    message = await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question=question,
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_option_id,
        explanation=f"This question is from category: {question_data.get('category', 'General')}",
        is_anonymous=False
    )
    
    # Store the poll message for reference
    context.user_data["quiz_message_id"] = message.message_id
    
    # Log that a quiz was started
    logger.info(f"Started quiz for user {update.effective_user.name}")

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for when a user answers a poll"""
    answer = update.poll_answer
    user_id = answer.user.id
    user_name = answer.user.name
    
    # Get the selected option
    selected_option = answer.option_ids[0] if answer.option_ids else None
    
    # Get the correct answer from user_data
    correct_option = context.user_data.get("quiz_correct_answer")
    
    # Check if the answer is correct
    is_correct = (selected_option == correct_option)
    
    # Update user stats
    update_user_stats(user_id, user_name, is_correct)
    
    # Send feedback message
    await context.bot.send_message(
        chat_id=user_id,
        text=f"{'✅ Correct!' if is_correct else '❌ Wrong!'} Use /play to try another quiz."
    )

async def add_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Command to start adding a new quiz question"""
    await update.message.reply_text(
        "Let's create a new quiz question.\n\n"
        "First, send me the question text.\n"
        "For example: 'What is the capital of France?'\n\n"
        "Type /cancel to abort."
    )
    return QUESTION

async def get_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receiving the question text"""
    question_text = update.message.text
    context.user_data["quiz_question"] = question_text
    
    await update.message.reply_text(
        "Great! Now send me the answer options, one per line.\n"
        "For example:\n"
        "Paris\n"
        "London\n"
        "Berlin\n"
        "Rome\n\n"
        "Type /cancel to abort."
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
    
    context.user_data["quiz_options"] = options
    
    # Create option buttons for selecting the correct answer
    keyboard = []
    for i, option in enumerate(options):
        keyboard.append([InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"answer_{i}")])
    
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
    
    # Extract the answer index from callback data
    answer_idx = int(query.data.split('_')[1])
    
    # Get the quiz data from user_data
    question = context.user_data.get("quiz_question")
    options = context.user_data.get("quiz_options")
    
    # Generate a new question ID
    question_id = get_next_question_id()
    
    # Create new question dictionary
    new_question = {
        "id": question_id,
        "question": question,
        "options": options,
        "answer": answer_idx,
        "category": "User Created"
    }
    
    # Add to questions file
    questions = load_questions()
    questions.append(new_question)
    save_questions(questions)
    
    # Notify the user
    await query.edit_message_text(
        f"✅ Quiz question created successfully!\n\n"
        f"Question: {question}\n"
        f"Correct answer: {options[answer_idx]}\n\n"
        f"Use /play to try it out or /add to create another."
    )
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the quiz creation process"""
    await update.message.reply_text(
        "Quiz creation cancelled. Use /help to see available commands."
    )
    context.user_data.clear()
    return ConversationHandler.END

async def list_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available quizzes"""
    questions = load_questions()
    
    if not questions:
        await update.message.reply_text("No quiz questions available. Use /add to create some!")
        return
    
    # Group questions by category
    categories = {}
    for q in questions:
        category = q.get("category", "General")
        if category not in categories:
            categories[category] = []
        categories[category].append(q)
    
    # Format the response message
    message = "📋 *Available Quiz Questions* 📋\n\n"
    
    for category, questions in categories.items():
        message += f"*{category}* ({len(questions)})\n"
        for q in questions[:5]:  # Show only first 5 questions per category
            message += f"- ID {q['id']}: {q['question'][:30]}...\n"
        if len(questions) > 5:
            message += f"  ... and {len(questions) - 5} more\n"
        message += "\n"
    
    message += "Use /play to play a random quiz, or /edit [ID] to edit a specific question."
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def clone_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clone a quiz from a Telegram link"""
    command_args = context.args
    
    if command_args and command_args[0].startswith('http'):
        # If a URL is provided directly with the command
        url = command_args[0]
        await handle_quiz_url(update, context, url)
    else:
        # Otherwise, ask for the URL
        await update.message.reply_text(
            "Please send me the Telegram quiz link you want to clone.\n"
            "For example, a link from @QuizBot or another quiz bot.\n\n"
            "Type /cancel to abort."
        )
        return CLONE_URL

async def handle_quiz_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url=None):
    """Handle processing a quiz URL"""
    if not url:
        url = update.message.text
    
    # Parse the URL to extract quiz data
    quiz_data = parse_telegram_quiz_url(url)
    
    if not quiz_data:
        await update.message.reply_text(
            "Sorry, I couldn't extract a valid quiz from that link.\n"
            "Make sure it's a link to a Telegram quiz poll.\n\n"
            "You can use /add to create a quiz manually."
        )
        return ConversationHandler.END
    
    # Store the parsed data
    context.user_data["quiz_question"] = quiz_data["question"]
    context.user_data["quiz_options"] = quiz_data["options"]
    
    # Create option buttons for selecting the correct answer
    keyboard = []
    for i, option in enumerate(quiz_data["options"]):
        keyboard.append([InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"answer_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Ask the user to select the correct answer
    await update.message.reply_text(
        f"I found the following quiz:\n\n"
        f"Question: {quiz_data['question']}\n\n"
        f"Options:\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(quiz_data["options"])) + "\n\n"
        f"Now select which option is the correct answer:",
        reply_markup=reply_markup
    )
    
    return ANSWER

async def edit_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit an existing quiz"""
    command_args = context.args
    
    if not command_args:
        # Show list of quizzes for selection
        questions = load_questions()
        if not questions:
            await update.message.reply_text("No quiz questions available to edit.")
            return ConversationHandler.END
        
        keyboard = []
        # Show up to 10 questions for selection
        for q in questions[:10]:
            keyboard.append([InlineKeyboardButton(
                f"ID {q['id']}: {q['question'][:30]}...", 
                callback_data=f"edit_{q['id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select a quiz to edit:",
            reply_markup=reply_markup
        )
        return EDIT_SELECT
    else:
        # Try to get the question by ID
        try:
            question_id = int(command_args[0])
            question = get_question_by_id(question_id)
            
            if not question:
                await update.message.reply_text(f"No question found with ID {question_id}.")
                return ConversationHandler.END
            
            # Store the question for editing
            context.user_data["edit_question"] = question
            
            # Show edit options
            keyboard = [
                [InlineKeyboardButton("Edit Question Text", callback_data="edit_text")],
                [InlineKeyboardButton("Edit Options", callback_data="edit_options")],
                [InlineKeyboardButton("Change Correct Answer", callback_data="edit_answer")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Editing Quiz ID {question_id}:\n\n"
                f"Question: {question['question']}\n\n"
                f"Options:\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(question["options"])) + "\n\n"
                f"Correct answer: {question['options'][question['answer']]}\n\n"
                f"What would you like to edit?",
                reply_markup=reply_markup
            )
            
            return EDIT_SELECT
            
        except (ValueError, IndexError):
            await update.message.reply_text(
                "Invalid question ID. Use /list to see available quizzes and their IDs."
            )
            return ConversationHandler.END

async def edit_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing the question text"""
    query = update.callback_query
    await query.answer()
    
    question = context.user_data.get("edit_question")
    if not question:
        await query.edit_message_text("Error: No question being edited.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"Send me the new text for the question:\n\n"
        f"Current: {question['question']}\n\n"
        f"Type /cancel to abort."
    )
    
    return EDIT_QUESTION

async def edit_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle editing the options"""
    query = update.callback_query
    await query.answer()
    
    question = context.user_data.get("edit_question")
    if not question:
        await query.edit_message_text("Error: No question being edited.")
        return ConversationHandler.END
    
    current_options = "\n".join(question["options"])
    
    await query.edit_message_text(
        f"Send me the new options, one per line:\n\n"
        f"Current options:\n{current_options}\n\n"
        f"Type /cancel to abort."
    )
    
    return EDIT_OPTIONS

async def edit_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting the correct answer"""
    query = update.callback_query
    await query.answer()
    
    question = context.user_data.get("edit_question")
    if not question:
        await query.edit_message_text("Error: No question being edited.")
        return ConversationHandler.END
    
    # Create option buttons for selecting the correct answer
    keyboard = []
    for i, option in enumerate(question["options"]):
        keyboard.append([InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"editanswer_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Select the new correct answer:\n\n"
        f"Current correct answer: {question['options'][question['answer']]}\n\n"
        f"Type /cancel to abort.",
        reply_markup=reply_markup
    )
    
    return EDIT_ANSWER

async def save_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a forwarded quiz from Telegram"""
    if not update.message.forward_from_message_id:
        await update.message.reply_text(
            "This command is for saving forwarded quiz polls.\n"
            "Forward a quiz poll to me and then use this command.\n\n"
            "Alternatively, you can use /add to create a quiz manually."
        )
        return
    
    # Check if this is a forwarded poll
    if update.message.poll:
        poll = update.message.poll
        
        # Check if it's a quiz poll
        if poll.type != Poll.QUIZ:
            await update.message.reply_text(
                "This appears to be a regular poll, not a quiz poll.\n"
                "I can only save quiz polls with a correct answer."
            )
            return
        
        # Extract question and options
        question_text = poll.question
        options = [opt.text for opt in poll.options]
        
        # Store for later processing
        context.user_data["quiz_question"] = question_text
        context.user_data["quiz_options"] = options
        
        # Create option buttons for selecting the correct answer
        keyboard = []
        for i, option in enumerate(options):
            keyboard.append([InlineKeyboardButton(f"{i+1}. {option}", callback_data=f"answer_{i}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"I found this quiz poll:\n\n"
            f"Question: {question_text}\n\n"
            f"Options:\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options)) + "\n\n"
            f"Which option is the correct answer?",
            reply_markup=reply_markup
        )
        
        return ANSWER
    else:
        await update.message.reply_text(
            "The forwarded message doesn't appear to contain a quiz poll.\n"
            "Try forwarding a quiz poll from another bot like @QuizBot."
        )
        return ConversationHandler.END

async def remove_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a quiz by ID"""
    command_args = context.args
    
    if not command_args:
        # Show list of quizzes for selection
        questions = load_questions()
        if not questions:
            await update.message.reply_text("No quiz questions available to remove.")
            return
        
        keyboard = []
        # Show up to 10 questions for selection
        for q in questions[:10]:
            keyboard.append([InlineKeyboardButton(
                f"ID {q['id']}: {q['question'][:30]}...", 
                callback_data=f"remove_{q['id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Select a quiz to remove:",
            reply_markup=reply_markup
        )
    else:
        # Try to get the question by ID
        try:
            question_id = int(command_args[0])
            question = get_question_by_id(question_id)
            
            if not question:
                await update.message.reply_text(f"No question found with ID {question_id}.")
                return
            
            # Create confirm/cancel buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, delete it", callback_data=f"confirm_remove_{question_id}"),
                    InlineKeyboardButton("❌ No, keep it", callback_data="cancel_remove")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Are you sure you want to delete this quiz?\n\n"
                f"ID: {question_id}\n"
                f"Question: {question['question']}\n"
                f"Category: {question.get('category', 'General')}",
                reply_markup=reply_markup
            )
            
        except (ValueError, IndexError):
            await update.message.reply_text(
                "Invalid question ID. Use /list to see available quizzes and their IDs."
            )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks for quiz deletion confirmation"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "cancel_remove":
        await query.edit_message_text("Quiz deletion cancelled.")
        return
    
    elif callback_data.startswith("confirm_remove_"):
        try:
            question_id = int(callback_data.split("_")[2])
            question = get_question_by_id(question_id)
            
            if not question:
                await query.edit_message_text(f"Error: Question ID {question_id} not found.")
                return
            
            # Delete the question
            if delete_question_by_id(question_id):
                await query.edit_message_text(f"✅ Quiz question ID {question_id} has been deleted.")
            else:
                await query.edit_message_text(f"❌ Failed to delete question ID {question_id}.")
        
        except (ValueError, IndexError) as e:
            await query.edit_message_text(f"Error processing request: {e}")
    
    elif callback_data.startswith("remove_"):
        try:
            question_id = int(callback_data.split("_")[1])
            question = get_question_by_id(question_id)
            
            if not question:
                await query.edit_message_text(f"Error: Question ID {question_id} not found.")
                return
            
            # Create confirm/cancel buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, delete it", callback_data=f"confirm_remove_{question_id}"),
                    InlineKeyboardButton("❌ No, keep it", callback_data="cancel_remove")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"Are you sure you want to delete this quiz?\n\n"
                f"ID: {question_id}\n"
                f"Question: {question['question']}\n"
                f"Category: {question.get('category', 'General')}",
                reply_markup=reply_markup
            )
            
        except (ValueError, IndexError) as e:
            await query.edit_message_text(f"Error processing request: {e}")

    elif callback_data.startswith("edit_"):
        if callback_data == "edit_text":
            await edit_question_text(update, context)
        elif callback_data == "edit_options":
            await edit_options(update, context)
        elif callback_data == "edit_answer":
            await edit_answer(update, context)
        else:
            try:
                # Handle selecting a question to edit
                question_id = int(callback_data.split("_")[1])
                question = get_question_by_id(question_id)
                
                if not question:
                    await query.edit_message_text(f"Error: Question ID {question_id} not found.")
                    return
                
                # Store the question for editing
                context.user_data["edit_question"] = question
                
                # Show edit options
                keyboard = [
                    [InlineKeyboardButton("Edit Question Text", callback_data="edit_text")],
                    [InlineKeyboardButton("Edit Options", callback_data="edit_options")],
                    [InlineKeyboardButton("Change Correct Answer", callback_data="edit_answer")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"Editing Quiz ID {question_id}:\n\n"
                    f"Question: {question['question']}\n\n"
                    f"Options:\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(question["options"])) + "\n\n"
                    f"Correct answer: {question['options'][question['answer']]}\n\n"
                    f"What would you like to edit?",
                    reply_markup=reply_markup
                )
            
            except (ValueError, IndexError) as e:
                await query.edit_message_text(f"Error processing request: {e}")
    
    elif callback_data.startswith("editanswer_"):
        try:
            # Extract the answer index from callback data
            answer_idx = int(callback_data.split('_')[1])
            
            # Get the question being edited
            question = context.user_data.get("edit_question")
            if not question:
                await query.edit_message_text("Error: No question being edited.")
                return ConversationHandler.END
            
            # Update the correct answer
            question["answer"] = answer_idx
            
            # Save the changes
            questions = load_questions()
            for i, q in enumerate(questions):
                if q.get("id") == question.get("id"):
                    questions[i] = question
                    break
            
            save_questions(questions)
            
            # Confirm the changes
            await query.edit_message_text(
                f"✅ Quiz updated successfully!\n\n"
                f"Question: {question['question']}\n"
                f"New correct answer: {question['options'][answer_idx]}\n\n"
                f"Use /list to see all quizzes or /play to try one."
            )
            
            # Clear user data
            context.user_data.clear()
            
            return ConversationHandler.END
            
        except (ValueError, IndexError) as e:
            await query.edit_message_text(f"Error updating answer: {e}")
            return ConversationHandler.END

def main():
    """Start the bot"""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

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
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(add_quiz_conv)
    
    # Add conversation handler for quiz cloning
    clone_quiz_conv = ConversationHandler(
        entry_points=[CommandHandler("clone", clone_quiz)],
        states={
            CLONE_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_url)],
            ANSWER: [CallbackQueryHandler(get_answer, pattern=r"^answer_")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
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
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(edit_quiz_conv)
    
    # Add handler for saving forwarded quizzes
    application.add_handler(CommandHandler("saveforward", save_forward))
    
    # Add callback query handler for button callbacks
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()

