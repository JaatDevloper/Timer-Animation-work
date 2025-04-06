"""
Web Scraper for Telegram Quiz Bot
This script scrapes web content to generate quiz questions
"""
import os
import json
import random
import trafilatura
from typing import List, Dict, Any

# Path to save scraped questions
QUESTIONS_FILE = 'data/questions.json'

def get_website_text_content(url: str) -> str:
    """
    Extract the main text content from a website
    
    Args:
        url: URL of the website to scrape
        
    Returns:
        Extracted text content
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        return text or ""
    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        return ""

def scrape_wikipedia_topic(topic: str) -> str:
    """
    Scrape content from a Wikipedia page about a specific topic
    
    Args:
        topic: The topic to search for on Wikipedia
        
    Returns:
        Extracted content
    """
    # Format the topic for Wikipedia URL
    formatted_topic = topic.replace(' ', '_')
    url = f"https://en.wikipedia.org/wiki/{formatted_topic}"
    
    # Get the content
    content = get_website_text_content(url)
    
    return content

def generate_question_from_content(content: str, topic: str) -> Dict[str, Any]:
    """
    This function generates a more meaningful question based on the content and topic.
    It extracts information from the content to create a relevant question.
    
    Args:
        content: Text content to generate questions from
        topic: The topic the content is about
        
    Returns:
        Question dictionary
    """
    # Simple template-based approach for different topics
    templates = [
        "What is the main characteristic of {topic}?",
        "Which of the following is associated with {topic}?",
        "What is {topic} primarily known for?",
        "Which statement about {topic} is correct?",
        "What is a key feature of {topic}?"
    ]
    
    # Select a random template
    question_template = random.choice(templates)
    question_text = question_template.format(topic=topic)
    
    # Create some plausible options based on content
    # This is a simplified approach and could be improved
    paragraphs = content.split('\n\n')
    valid_paragraphs = [p for p in paragraphs if len(p.split()) > 10]
    
    if not valid_paragraphs:
        return None
    
    # Pick a correct answer from the content
    correct_paragraph = random.choice(valid_paragraphs[:3] if len(valid_paragraphs) > 3 else valid_paragraphs)
    correct_answer = ' '.join(correct_paragraph.split()[:15]) + "..."
    
    # Generate incorrect options - simplified approach
    other_options = []
    for _ in range(3):
        # Pick a different paragraph for incorrect options if possible
        other_paragraphs = [p for p in valid_paragraphs if p != correct_paragraph]
        if other_paragraphs:
            paragraph = random.choice(other_paragraphs)
            option = ' '.join(paragraph.split()[:15]) + "..."
            other_options.append(option)
        else:
            # If not enough paragraphs, create generic incorrect options
            option = f"None of the statements about {topic} are true."
            other_options.append(option)
    
    # Combine and shuffle options
    options = [correct_answer] + other_options
    random.shuffle(options)
    
    # Find the index of the correct answer
    correct_index = options.index(correct_answer)
    
    # Get next available ID
    next_id = 1
    existing_questions = load_existing_questions()
    if existing_questions:
        next_id = max(q.get("id", 0) for q in existing_questions) + 1
    
    # Create the question dictionary
    question = {
        "id": next_id,
        "question": question_text,
        "options": options,
        "answer": correct_index,
        "category": topic
    }
    
    return question

def load_existing_questions() -> List[Dict[str, Any]]:
    """
    Load existing questions from the JSON file
    
    Returns:
        List of question dictionaries
    """
    # Ensure the data directory exists
    os.makedirs('data', exist_ok=True)
    
    if os.path.exists(QUESTIONS_FILE):
        try:
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            print(f"Error: {QUESTIONS_FILE} is not a valid JSON file.")
            return []
    return []

def save_questions(questions: List[Dict[str, Any]]) -> None:
    """
    Save questions to the JSON file
    
    Args:
        questions: List of question dictionaries
    """
    # Ensure the data directory exists
    os.makedirs('data', exist_ok=True)
    
    with open(QUESTIONS_FILE, 'w', encoding='utf-8') as file:
        json.dump(questions, file, ensure_ascii=False, indent=4)

def main():
    """Main function"""
    # Topics to scrape
    topics = [
        "Artificial Intelligence",
        "Quantum Computing", 
        "Solar System",
        "Climate Change",
        "Ancient Rome",
        "Renaissance Art",
        "Olympic Games",
        "World War II",
        "Blockchain Technology",
        "Human Genome Project"
    ]
    
    # Load existing questions
    existing_questions = load_existing_questions()
    print(f"Loaded {len(existing_questions)} existing questions")
    
    # Generate new questions
    new_questions = []
    for topic in topics:
        print(f"Scraping content for: {topic}")
        content = scrape_wikipedia_topic(topic)
        
        if content:
            question = generate_question_from_content(content, topic)
            if question:
                new_questions.append(question)
                print(f"Created question: {question['question']}")
        else:
            print(f"Failed to get content for {topic}")
    
    # Combine with existing questions and save
    all_questions = existing_questions + new_questions
    save_questions(all_questions)
    print(f"Saved {len(all_questions)} questions (added {len(new_questions)} new questions)")

if __name__ == "__main__":
    main()
