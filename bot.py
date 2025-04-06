from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import json
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Store this in .env later

# Load quiz data (for now we use local JSON)
try:
    with open("database/quiz_data.json", "r") as f:
        quizzes = json.load(f)
except:
    quizzes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Mega Quiz Bot!\nUse /play to start a quiz or /create to make your own."
    )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Start Quiz", callback_data="start_quiz")],
        [InlineKeyboardButton("Edit Quiz", callback_data="edit_quiz")]
    ]
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

