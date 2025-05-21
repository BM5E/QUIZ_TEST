import os
import json
import logging
import random
from datetime import datetime
from openai import OpenAI
from models import Book, StoredQuestion, db
from ai_service_manager import AIServiceManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Map AI service names to their client initialization functions
AI_SERVICE_CLIENTS = {
    'openai': lambda api_key: OpenAI(api_key=api_key),
    'anthropic': lambda api_key: None,  # Placeholder, would need to import Anthropic client
    'gemini': lambda api_key: None,     # Placeholder, would need to import Gemini client
}

def get_ai_client():
    """
    Get an AI client based on available API keys
    
    Returns:
        tuple: (client, service_name) or (None, None) if no clients are available
    """
    # Get the highest priority available API key
    service_name, api_key = AIServiceManager.get_api_key()
    
    if not service_name or not api_key:
        logger.error("No active AI API keys available")
        return None, None
    
    # Check if we have an initialization function for this service
    if service_name not in AI_SERVICE_CLIENTS:
        logger.error(f"No client implementation for AI service: {service_name}")
        return None, None
    
    try:
        # Initialize the client
        client = AI_SERVICE_CLIENTS[service_name](api_key)
        return client, service_name
    except Exception as e:
        logger.error(f"Error initializing {service_name} client: {str(e)}")
        # Deactivate the problematic API key
        AIServiceManager.deactivate_api_key(api_name=service_name, api_key=api_key)
        return None, None

def generate_comprehensive_question_set(book):
    """
    Generate a comprehensive set of quiz questions (198 questions) for a book
    33 questions per difficulty level and question type combination
    
    Args:
        book: Book object or book details dictionary
        
    Returns:
        list: List of question dictionaries
    """
    # Ensure we have a dictionary with book details
    if isinstance(book, Book):
        book_details = {
            'title': book.title,
            'author': book.author,
            'description': book.description,
            'publication_year': book.publication_year,
            'genre': book.genre
        }
    else:
        book_details = book
    
    # Questions to generate per difficulty and type
    questions_per_category = 33
    
    # Question types and difficulty levels
    question_types = ['choice', 'blank']
    difficulty_levels = ['easy', 'middle', 'hard']
    
    # Will store all generated questions
    all_questions = []
    
    # Try up to 3 different AI services if needed
    for attempt in range(3):
        client, service_name = get_ai_client()
        
        if not client:
            logger.error(f"Failed to get AI client on attempt {attempt+1}/3")
            if attempt == 2:  # Last attempt failed
                return []
            continue  # Try next service
        
        try:
            logger.info(f"Using {service_name} to generate questions")
            
            for difficulty in difficulty_levels:
                for q_type in question_types:
                    # Check if we already have questions for this category
                    existing_count = sum(1 for q in all_questions if q['difficulty'] == difficulty and q['question_type'] == q_type)
                    if existing_count >= questions_per_category:
                        continue
                    
                    # Number of questions still needed for this category
                    questions_needed = questions_per_category - existing_count
                    
                    # Generate questions based on the AI service
                    if service_name == 'openai':
                        questions = generate_questions_openai(client, book_details, questions_needed, difficulty, q_type)
                    elif service_name == 'anthropic':
                        questions = generate_questions_anthropic(client, book_details, questions_needed, difficulty, q_type)
                    elif service_name == 'gemini':
                        questions = generate_questions_gemini(client, book_details, questions_needed, difficulty, q_type)
                    else:
                        questions = []
                    
                    # Add valid questions to our collection
                    for q in questions:
                        # Ensure question has all required fields
                        if validate_question(q, q_type):
                            # Add difficulty level to the question
                            q['difficulty'] = difficulty
                            all_questions.append(q)
            
            # If we've generated all the questions needed, break the loop
            if len(all_questions) == questions_per_category * len(difficulty_levels) * len(question_types):
                break
            
        except Exception as e:
            logger.error(f"Error generating questions with {service_name}: {str(e)}")
            # Deactivate the problematic API key
            AIServiceManager.deactivate_api_key(api_name=service_name)
    
    return all_questions

def generate_questions_openai(client, book_details, num_questions, difficulty, question_type):
    """
    Generate quiz questions using OpenAI
    
    Args:
        client: OpenAI client instance
        book_details: Dictionary with book information
        num_questions: Number of questions to generate
        difficulty: Difficulty level ('easy', 'middle', 'hard')
        question_type: Type of question ('choice', 'blank')
        
    Returns:
        list: List of question dictionaries
    """
    # Build appropriate difficulty description
    difficulty_descriptions = {
        'easy': "simple, factual questions that someone with basic knowledge of the book would know",
        'middle': "moderately challenging questions that require good familiarity with the book's content",
        'hard': "difficult questions that test deep knowledge of the book's themes, character motivations, and subtle plot details"
    }
    
    # Custom format instructions based on question type
    if question_type == 'choice':
        format_instructions = f"""
        Each question should follow this exact JSON format:
        {{
            "question_text": "The question text",
            "question_type": "choice",
            "correct_answer": "The correct option EXACTLY as written in the options array",
            "option_a": "First option",
            "option_b": "Second option",
            "option_c": "Third option",
            "option_d": "Fourth option"
        }}
        
        For multiple choice questions:
        - Ensure the correct_answer matches EXACTLY one of the options
        - Make all options plausible and similar in length
        - Don't use "all of the above" or "none of the above" options
        - Options should be clear and distinct from each other
        """
    else:  # blank
        format_instructions = f"""
        Each question should follow this exact JSON format:
        {{
            "question_text": "The question text with a _____ where the answer should go",
            "question_type": "blank",
            "correct_answer": "The word or short phrase that belongs in the blank"
        }}
        
        For fill-in-the-blank questions:
        - The correct_answer should be 1-3 words maximum
        - Ensure there's only one reasonable answer
        - The blank should be indicated with exactly five underscores (_____) in the question_text
        """
    
    # Construct the full prompt
    book_info = f"Title: {book_details['title']}\nAuthor: {book_details['author']}\n"
    if 'description' in book_details and book_details['description']:
        book_info += f"Description: {book_details['description']}\n"
    
    prompt = f"""
    Create {num_questions} {difficulty} quiz questions about this book:
    
    {book_info}
    
    The questions should be {difficulty_descriptions[difficulty]}.
    
    {format_instructions}
    
    Return the questions in a JSON array format under a 'questions' key.
    Each question must be specifically about this book, not general literature questions.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a literary expert creating educational quiz questions about books."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content
        if not result_text:
            logger.error("Empty response from OpenAI API")
            return []
        
        result = json.loads(result_text)
        
        # Extract questions array
        if 'questions' in result:
            questions = result['questions']
        elif isinstance(result, list):
            questions = result
        else:
            # Look for any array in the response
            for key, value in result.items():
                if isinstance(value, list) and len(value) > 0:
                    questions = value
                    break
            else:
                questions = []
        
        return questions
        
    except Exception as e:
        logger.error(f"Error generating questions with OpenAI: {str(e)}")
        return []

def generate_questions_anthropic(client, book_details, num_questions, difficulty, question_type):
    """
    Generate quiz questions using Anthropic (Claude)
    Placeholder function - would need to be implemented with actual Anthropic API
    """
    # Placeholder implementation
    logger.info("Anthropic question generation not yet implemented")
    return []

def generate_questions_gemini(client, book_details, num_questions, difficulty, question_type):
    """
    Generate quiz questions using Google's Gemini
    Placeholder function - would need to be implemented with actual Gemini API
    """
    # Placeholder implementation
    logger.info("Gemini question generation not yet implemented")
    return []

def validate_question(question, expected_type):
    """
    Validate that a question has all required fields
    
    Args:
        question: Question dictionary to validate
        expected_type: Expected question type ('choice' or 'blank')
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Check basic required fields
    if 'question_text' not in question or not question['question_text']:
        return False
    
    if 'question_type' not in question:
        if expected_type == 'choice' and all(key in question for key in ['option_a', 'option_b', 'option_c', 'option_d']):
            question['question_type'] = 'choice'
        elif expected_type == 'blank' and '____' in question.get('question_text', ''):
            question['question_type'] = 'blank'
        else:
            return False
    
    if 'correct_answer' not in question or not question['correct_answer']:
        return False
    
    # Validate multiple choice questions
    if question['question_type'] == 'choice':
        required_options = ['option_a', 'option_b', 'option_c', 'option_d']
        if not all(key in question for key in required_options):
            return False
        
        # Ensure correct_answer matches one of the options
        options = [question.get(opt) for opt in required_options]
        if question['correct_answer'] not in options:
            # Attempt to fix by setting it to the first option
            question['correct_answer'] = question['option_a']
    
    # Validate fill-in-the-blank questions
    elif question['question_type'] == 'blank':
        if '____' not in question['question_text']:
            # Add blank if missing
            if '?' in question['question_text']:
                question['question_text'] = question['question_text'].replace('?', '_____?')
            else:
                question['question_text'] += ' _____'
    
    return True

def save_questions_to_database(book_id, questions):
    """
    Save generated questions to the database
    
    Args:
        book_id: ID of the book in the database
        questions: List of question dictionaries
        
    Returns:
        int: Number of questions successfully saved
    """
    saved_count = 0
    
    try:
        # Get the book
        book = Book.query.get(book_id)
        if not book:
            logger.error(f"Book with ID {book_id} not found")
            return 0
        
        # Process each question
        for q in questions:
            try:
                # Create new question
                new_question = StoredQuestion()
                new_question.book_id = book_id
                new_question.question_text = q.get('question_text', '')
                new_question.question_type = q.get('question_type', 'choice')
                new_question.difficulty = q.get('difficulty', 'middle')
                new_question.correct_answer = q.get('correct_answer', '')
                
                # Add multiple choice options if available
                if q.get('question_type') == 'choice':
                    new_question.option_a = q.get('option_a', '')
                    new_question.option_b = q.get('option_b', '')
                    new_question.option_c = q.get('option_c', '')
                    new_question.option_d = q.get('option_d', '')
                
                db.session.add(new_question)
                saved_count += 1
                
                # Commit in batches of 50 to avoid long transactions
                if saved_count % 50 == 0:
                    db.session.commit()
            
            except Exception as e:
                logger.error(f"Error saving question: {str(e)}")
                # Continue with other questions
        
        # Final commit for remaining questions
        db.session.commit()
        logger.info(f"Saved {saved_count} questions for book ID {book_id}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving questions to database: {str(e)}")
    
    return saved_count

def get_stored_questions_for_quiz(book_id, num_questions=10, difficulty='middle', question_type='choice'):
    """
    Get stored questions for a quiz
    
    Args:
        book_id: ID of the book in the database
        num_questions: Number of questions to return
        difficulty: Difficulty level ('easy', 'middle', 'hard', or 'mixed')
        question_type: Type of questions ('choice', 'blank', or 'mixed')
        
    Returns:
        list: List of question dictionaries
    """
    try:
        # Start with a base query
        query = StoredQuestion.query.filter_by(book_id=book_id)
        
        # Apply filters based on parameters
        if difficulty != 'mixed':
            query = query.filter_by(difficulty=difficulty)
        
        if question_type != 'mixed':
            query = query.filter_by(question_type=question_type)
        
        # Get all matching questions
        all_questions = query.all()
        
        # If no stored questions found, return empty list
        if not all_questions:
            return []
        
        # For mixed difficulty/type, ensure we get a balanced mix
        if difficulty == 'mixed' or question_type == 'mixed':
            # Organize questions by difficulty and type
            organized = {}
            for q in all_questions:
                key = (q.difficulty, q.question_type)
                if key not in organized:
                    organized[key] = []
                organized[key].append(q)
            
            # Determine how many questions to take from each category
            categories = list(organized.keys())
            questions_per_category = max(1, num_questions // len(categories))
            
            # Select questions from each category
            selected = []
            for key, questions in organized.items():
                # Shuffle and take up to questions_per_category
                random.shuffle(questions)
                selected.extend(questions[:questions_per_category])
            
            # If we need more questions to reach the requested count
            while len(selected) < num_questions and len(all_questions) > len(selected):
                # Find questions not already selected
                remaining = [q for q in all_questions if q not in selected]
                if not remaining:
                    break
                
                # Add a random remaining question
                selected.append(random.choice(remaining))
            
            # Limit to requested number
            selected = selected[:num_questions]
        else:
            # Simple random selection for non-mixed categories
            random.shuffle(all_questions)
            selected = all_questions[:num_questions]
        
        # Convert questions to dictionaries
        result = []
        for q in selected:
            question_dict = {
                'question': q.question_text,
                'question_type': q.question_type,
                'correct_answer': q.correct_answer
            }
            
            # Add multiple choice options if applicable
            if q.question_type == 'choice':
                question_dict['options'] = [q.option_a, q.option_b, q.option_c, q.option_d]
            
            result.append(question_dict)
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting stored questions: {str(e)}")
        return []