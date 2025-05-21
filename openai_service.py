import os
import json
import logging
import random
from openai import OpenAI
from models import APIKey

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize client
client = None

def initialize_openai():
    """Initialize the OpenAI client with a key from the database or environment"""
    global client
    try:
        # Try to get key from database first
        api_key_record = APIKey.query.filter_by(api_name='openai', is_active=True).first()
        if api_key_record:
            client = OpenAI(api_key=api_key_record.api_key)
            return True
        
        # Fall back to environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key)
            return True
        
        logger.warning("No OpenAI API key found in database or environment")
        return False
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        return False

def get_book_or_author_info(query, search_type):
    """
    Get information about a book or author using OpenAI.
    
    Args:
        query (str): The book title or author name to search for
        search_type (str): Either 'book' or 'author'
        
    Returns:
        list: List of dictionaries containing book or author information
    """
    global client
    
    # Try to initialize if not already initialized
    if client is None:
        initialize_openai()
    
    # Check if OpenAI client is initialized (API key exists)
    if client is None:
        logger.error("OpenAI API key is missing. Cannot get book/author information.")
        # Return a fallback response that explains the issue
        if search_type == 'book':
            return [{
                'title': query,
                'author': 'Unknown',
                'publication_year': 'Unknown',
                'genre': 'Unknown',
                'description': 'Book information unavailable. Please provide an OpenAI API key to enable this feature.',
                'themes': ['Information unavailable'],
                'key_characters': ['Information unavailable'],
                'awards': ['Information unavailable']
            }]
        else:  # author
            return [{
                'name': query,
                'birth_year': 'Unknown',
                'death_year': 'Unknown',
                'nationality': 'Unknown',
                'biography': 'Author information unavailable. Please provide an OpenAI API key to enable this feature.',
                'notable_works': ['Information unavailable'],
                'writing_style': 'Information unavailable',
                'influence': 'Information unavailable'
            }]
    
    try:
        if search_type == 'book':
            prompt = f"""
            Please provide detailed information about the book "{query}" in JSON format.
            Include the following fields:
            - title: The full title of the book
            - author: The author's name
            - publication_year: When it was published
            - genre: The genre(s) of the book
            - description: A detailed summary of the book (at least 100 words)
            - themes: Main themes of the book
            - key_characters: List of key characters and brief descriptions
            - awards: Any major awards or recognition the book received
            
            Return a list of books that match this query, with the most relevant first.
            Format as a JSON array of objects with the fields above.
            """
        else:  # author
            prompt = f"""
            Please provide detailed information about the author "{query}" in JSON format.
            Include the following fields:
            - name: The author's full name
            - birth_year: Year of birth (if known)
            - death_year: Year of death (if applicable)
            - nationality: The author's nationality
            - biography: A detailed biography (at least 150 words)
            - notable_works: List of the author's most notable works
            - writing_style: Description of their writing style and themes
            - influence: Their influence on literature
            
            Return a list of authors that match this query, with the most relevant first.
            Format as a JSON array of objects with the fields above.
            """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a literary database expert providing accurate information about books and authors."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content
        if result_text:
            result = json.loads(result_text)
            
            # If result is not a list, wrap it in a list
            if isinstance(result, dict):
                if "results" in result:
                    return result["results"]
                return [result]
            
            return result
        else:
            logger.error("Empty response from OpenAI API")
            raise ValueError("Empty response from OpenAI API")
        
    except Exception as e:
        logger.error(f"Error getting book/author info: {str(e)}")
        # Return fallback results instead of empty list
        if search_type == 'book':
            return [{
                'title': query,
                'author': 'Unknown',
                'publication_year': 'Unknown',
                'genre': 'Fiction',
                'description': f'Information for "{query}" is temporarily unavailable. The search system is currently experiencing high traffic or rate limits. Please try again later or try a different search term.',
                'themes': ['Information temporarily unavailable'],
                'key_characters': ['Information temporarily unavailable'],
                'awards': ['Information temporarily unavailable']
            }]
        else:  # author
            return [{
                'name': query,
                'birth_year': 'Unknown',
                'death_year': 'Unknown',
                'nationality': 'Unknown',
                'biography': f'Information for "{query}" is temporarily unavailable. The search system is currently experiencing high traffic or rate limits. Please try again later or try a different search term.',
                'notable_works': ['Information temporarily unavailable'],
                'writing_style': 'Information temporarily unavailable',
                'influence': 'Information temporarily unavailable'
            }]

def generate_quiz_questions(book_or_author, search_type, num_questions=5, challenge_level='middle', question_type='choice'):
    """
    Generate quiz questions about a book or author using OpenAI.
    
    Args:
        book_or_author (str): The book title or author name
        search_type (str): Either 'book' or 'author'
        num_questions (int): Number of questions to generate
        challenge_level (str): 'easy', 'middle', or 'hard'
        question_type (str): 'choice', 'blank', or 'mixed'
        
    Returns:
        list: List of dictionaries containing quiz questions
    """
    # Check if OpenAI client is initialized (API key exists)
    if client is None:
        logger.error("OpenAI API key is missing. Using fallback questions.")
        return get_fallback_quiz_questions(book_or_author, search_type, num_questions, question_type)
    
    try:
        # For mixed question types, decide how many of each type to include
        question_types = []
        if question_type == 'mixed':
            # Create a mix of multiple-choice and fill-in-the-blank
            choice_count = num_questions // 2 + (num_questions % 2)
            blank_count = num_questions - choice_count
            
            question_types = ['choice'] * choice_count + ['blank'] * blank_count
            random.shuffle(question_types)
        else:
            question_types = [question_type] * num_questions
        
        # Build prompt based on difficulty level
        difficulty_descriptions = {
            'easy': "simple, factual questions that someone with basic knowledge would know",
            'middle': "moderately challenging questions that require good familiarity with the subject",
            'hard': "difficult questions that test deep knowledge and understanding of nuances"
        }
        
        prompt = f"""
        Create {num_questions} quiz questions about the {search_type} "{book_or_author}".
        
        The difficulty level should be {challenge_level}: {difficulty_descriptions[challenge_level]}
        
        For each question, provide:
        """
        
        # Add specific format instructions based on question types
        questions = []
        
        for i, q_type in enumerate(question_types):
            if q_type == 'choice':
                sub_prompt = f"""
                Question {i+1} should be multiple-choice with this format:
                {{
                    "question": "The question text",
                    "question_type": "choice",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "The correct option (exactly as written in options)"
                }}
                
                For multiple-choice questions:
                - Ensure the correct answer is one of the exact options provided
                - Make all options plausible
                - Don't use obvious incorrect answers
                - Don't use "All of the above" or "None of the above"
                """
            else:  # blank
                sub_prompt = f"""
                Question {i+1} should be fill-in-the-blank with this format:
                {{
                    "question": "The question text with a _____ for the answer",
                    "question_type": "blank",
                    "correct_answer": "The word or short phrase that fills the blank"
                }}
                
                For fill-in-the-blank questions:
                - Keep answers short (1-3 words)
                - Make the answers specific but not obscure
                - Ensure there's only one reasonable answer
                """
            
            prompt += sub_prompt
        
        prompt += """
        Return the questions in a JSON array. Ensure the questions test knowledge about different aspects of the subject.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a literary quiz expert creating challenging and educational questions."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=1500
        )
        
        result_text = response.choices[0].message.content
        if result_text:
            result = json.loads(result_text)
            
            # Handle different possible structures of the result
            if isinstance(result, dict):
                if "questions" in result:
                    questions = result["questions"]
                elif "quiz" in result:
                    questions = result["quiz"]
                else:
                    # Try to extract a list from the first key found
                    for key, value in result.items():
                        if isinstance(value, list):
                            questions = value
                            break
            elif isinstance(result, list):
                questions = result
            
            # Validate the structure of each question
            validated_questions = []
            for q in questions:
                # Ensure required fields are present
                if "question" not in q:
                    continue
                    
                # Set default question type if not present
                if "question_type" not in q:
                    if "options" in q:
                        q["question_type"] = "choice"
                    else:
                        q["question_type"] = "blank"
                        
                # Validate multiple choice questions
                if q.get("question_type") == "choice":
                    if "options" not in q or "correct_answer" not in q:
                        continue
                    if len(q["options"]) != 4:
                        # Ensure we have exactly 4 options
                        continue
                    if q["correct_answer"] not in q["options"]:
                        # Fix correct answer if it doesn't match options
                        if isinstance(q["correct_answer"], int):
                            # If it's an index, use the actual option
                            q["correct_answer"] = q["options"][q["correct_answer"] % len(q["options"])]
                        else:
                            # Otherwise, set it to the first option
                            q["correct_answer"] = q["options"][0]
                            
                # Validate fill-in-the-blank questions
                elif q.get("question_type") == "blank":
                    if "correct_answer" not in q:
                        continue
                        
                validated_questions.append(q)
                
            # Limit to requested number
            return validated_questions[:num_questions]
        else:
            logger.error("Empty response from OpenAI API")
            raise ValueError("Empty response from OpenAI API")
        
    except Exception as e:
        logger.error(f"Error generating quiz questions: {str(e)}")
        return get_fallback_quiz_questions(book_or_author, search_type, num_questions, question_type)

def get_fallback_quiz_questions(book_or_author, search_type, num_questions=5, question_type='choice'):
    """
    Generate fallback quiz questions when the API fails or rate limits are hit.
    
    Args:
        book_or_author (str): The book title or author name
        search_type (str): Either 'book' or 'author'
        num_questions (int): Number of questions to generate
        question_type (str): 'choice', 'blank', or 'mixed'
        
    Returns:
        list: List of dictionaries containing quiz questions
    """
    # Generic literary questions that can work for most books/authors
    book_questions = [
        {
            "question": f"Which of the following could be a theme in {book_or_author}?",
            "question_type": "choice",
            "options": ["Love and loss", "Journey and discovery", "Power and corruption", "Identity and self-discovery"],
            "correct_answer": "Identity and self-discovery"
        },
        {
            "question": "Which narrative perspective is commonly used in fiction?",
            "question_type": "choice",
            "options": ["First person", "Second person", "Third person limited", "Third person omniscient"],
            "correct_answer": "Third person limited"
        },
        {
            "question": "What is the term for the main character in a story?",
            "question_type": "choice",
            "options": ["Protagonist", "Antagonist", "Deuteragonist", "Narrator"],
            "correct_answer": "Protagonist"
        },
        {
            "question": "What literary device involves comparing two unlike things using 'like' or 'as'?",
            "question_type": "choice",
            "options": ["Simile", "Metaphor", "Alliteration", "Hyperbole"],
            "correct_answer": "Simile"
        },
        {
            "question": "What is the climax of a story?",
            "question_type": "choice",
            "options": ["The most intense point", "The opening scene", "The final paragraph", "The author's biography"],
            "correct_answer": "The most intense point"
        },
        {
            "question": "In literature, the _____ is the opposing force that creates conflict for the protagonist.",
            "question_type": "blank",
            "correct_answer": "antagonist"
        },
        {
            "question": "A story told from the perspective of 'I' or 'we' is written in _____ person.",
            "question_type": "blank",
            "correct_answer": "first"
        },
        {
            "question": "The _____ is where and when a story takes place.",
            "question_type": "blank",
            "correct_answer": "setting"
        }
    ]
    
    author_questions = [
        {
            "question": f"Which of these might be true about {book_or_author}'s writing style?",
            "question_type": "choice",
            "options": ["Poetic and descriptive", "Concise and direct", "Stream of consciousness", "Technical and detailed"],
            "correct_answer": "Poetic and descriptive"
        },
        {
            "question": "Which of these periods might have influenced literature?",
            "question_type": "choice",
            "options": ["Romanticism", "Modernism", "Post-modernism", "Renaissance"],
            "correct_answer": "Modernism"
        },
        {
            "question": "Which of these might be a common theme in an author's work?",
            "question_type": "choice",
            "options": ["Social inequality", "Space exploration", "Underwater civilizations", "Dinosaur resurrection"],
            "correct_answer": "Social inequality"
        },
        {
            "question": "Where might an author draw inspiration from?",
            "question_type": "choice",
            "options": ["Personal experiences", "Historical events", "Cultural traditions", "All of these sources"],
            "correct_answer": "All of these sources"
        },
        {
            "question": "A writer who focuses on creating tension and fear is likely writing in which genre?",
            "question_type": "choice",
            "options": ["Horror", "Romance", "Science Fiction", "Comedy"],
            "correct_answer": "Horror"
        },
        {
            "question": "An author's unique way of writing, including word choice and sentence structure, is called their _____.",
            "question_type": "blank",
            "correct_answer": "style"
        },
        {
            "question": "The time period in which an author lived and wrote is critical to understanding their _____.",
            "question_type": "blank",
            "correct_answer": "context"
        },
        {
            "question": "An author's _____ refers to the impact their work has had on other writers and on literature as a whole.",
            "question_type": "blank",
            "correct_answer": "legacy"
        }
    ]
    
    # Choose the appropriate question set
    question_set = book_questions if search_type == 'book' else author_questions
    
    # Filter by question type if needed
    if question_type != 'mixed':
        question_set = [q for q in question_set if q['question_type'] == question_type]
    
    # If we don't have enough questions of the requested type, add some from the other type
    if len(question_set) < num_questions:
        other_set = author_questions if search_type == 'book' else book_questions
        if question_type != 'mixed':
            other_set = [q for q in other_set if q['question_type'] == question_type]
        question_set.extend(other_set)
    
    # Shuffle and return the requested number of questions
    random.shuffle(question_set)
    return question_set[:num_questions]