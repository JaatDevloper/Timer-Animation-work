from pyrogram import Client
import json
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

app = Client("user_scraper_session", api_id=API_ID, api_hash=API_HASH)

# Load current quiz data
try:
    with open("database/quiz_data.json", "r") as f:
        quizzes = json.load(f)
except:
    quizzes = {}

@app.on_message()
def get_quiz(client, message):
    if message.poll:
        question = message.poll.question
        options = [opt.text for opt in message.poll.options]
        correct_id = next((i for i, o in enumerate(message.poll.options) if o.is_correct), -1)
        quiz_title = message.chat.title or "Imported Quiz"

        quiz_id = f"{message.chat.id}_{message.message_id}"
        quizzes[quiz_id] = {
            "title": quiz_title,
            "question": question,
            "options": options,
            "correct_id": correct_id
        }

        print(f"Saved quiz: {question}")

        with open("database/quiz_data.json", "w") as f:
            json.dump(quizzes, f, indent=2)

app.run()
