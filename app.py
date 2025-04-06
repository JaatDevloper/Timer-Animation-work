"""
A simple Flask web application for the Telegram Quiz Bot
"""
import os
import json
import logging
from flask import Flask, jsonify, render_template_string

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Data files
QUESTIONS_FILE = 'data/questions.json'
USERS_FILE = 'data/users.json'

# HTML template for the index page
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Quiz Bot - Status</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>
        body {
            padding-top: 2rem;
        }
        .status-card {
            max-width: 800px;
            margin: 0 auto;
        }
        .status-badge {
            font-size: 1rem;
            padding: 0.5rem 1rem;
        }
        .stats-container {
            margin-top: 2rem;
        }
    </style>
</head>
<body data-bs-theme="dark">
    <div class="container">
        <div class="card status-card">
            <div class="card-header">
                <h1 class="text-center">Telegram Quiz Bot</h1>
            </div>
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center">
                    <h3>Bot Status</h3>
                    <span class="badge bg-success status-badge">Online</span>
                </div>
                
                <div class="stats-container">
                    <h4>Statistics</h4>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="card mb-3">
                                <div class="card-body">
                                    <h5 class="card-title">Quiz Questions</h5>
                                    <p class="card-text display-4">{{ stats.total_questions }}</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card mb-3">
                                <div class="card-body">
                                    <h5 class="card-title">Registered Users</h5>
                                    <p class="card-text display-4">{{ stats.total_users }}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card mb-3">
                        <div class="card-header">
                            <h5>Category Breakdown</h5>
                        </div>
                        <div class="card-body">
                            <ul class="list-group">
                                {% for category, count in stats.categories.items() %}
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    {{ category }}
                                    <span class="badge bg-primary rounded-pill">{{ count }}</span>
                                </li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                </div>
                
                <div class="mt-4">
                    <h4>How to Access</h4>
                    <p>Find the bot on Telegram: <a href="https://t.me/your_bot_username" target="_blank">@your_bot_username</a></p>
                    <p>Available commands:</p>
                    <ul>
                        <li><code>/start</code> - Start the bot</li>
                        <li><code>/help</code> - Show help information</li>
                        <li><code>/play</code> - Play a quiz</li>
                        <li><code>/stats</code> - View your statistics</li>
                        <li><code>/add</code> - Create a new quiz question</li>
                        <li><code>/list</code> - List all quizzes</li>
                        <li><code>/clone</code> - Clone a quiz from a link</li>
                        <li><code>/edit</code> - Edit an existing quiz</li>
                        <li><code>/remove</code> - Delete a quiz</li>
                    </ul>
                </div>
            </div>
            <div class="card-footer text-center">
                <p>&copy; 2025 Telegram Quiz Bot</p>
            </div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    """Home page with bot status"""
    stats = get_bot_stats()
    return render_template_string(INDEX_TEMPLATE, stats=stats)

@app.route('/api/stats')
def api_stats():
    """API endpoint for bot statistics"""
    return jsonify(get_bot_stats())

def get_bot_stats():
    """Get statistics about the bot usage"""
    stats = {
        'total_questions': 0,
        'total_users': 0,
        'categories': {}
    }
    
    # Get question statistics
    try:
        if os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as file:
                questions = json.load(file)
                stats['total_questions'] = len(questions)
                
                # Count questions by category
                for q in questions:
                    category = q.get('category', 'Uncategorized')
                    if category not in stats['categories']:
                        stats['categories'][category] = 0
                    stats['categories'][category] += 1
    except Exception as e:
        logger.error(f"Error reading questions file: {e}")
    
    # Get user statistics
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as file:
                users = json.load(file)
                stats['total_users'] = len(users)
    except Exception as e:
        logger.error(f"Error reading users file: {e}")
    
    return stats

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
