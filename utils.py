import logging
from openai_service import get_book_or_author_info

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_book_info(book_title):
    """
    Get information about a book using OpenAI.
    
    Args:
        book_title (str): The book title to search for
        
    Returns:
        dict: Dictionary containing book information
    """
    results = get_book_or_author_info(book_title, 'book')
    return results[0] if results else None

def get_author_info(author_name):
    """
    Get information about an author using OpenAI.
    
    Args:
        author_name (str): The author name to search for
        
    Returns:
        dict: Dictionary containing author information
    """
    results = get_book_or_author_info(author_name, 'author')
    return results[0] if results else None

def format_score(score):
    """
    Format a numerical score as a percentage string
    
    Args:
        score (float): The score to format
        
    Returns:
        str: Formatted score string
    """
    return f"{int(score)}%"

def get_quiz_emoji(score):
    """
    Get an emoji based on the quiz score
    
    Args:
        score (float): The quiz score
        
    Returns:
        str: An emoji representing the score
    """
    if score >= 90:
        return "🏆"
    elif score >= 80:
        return "🌟"
    elif score >= 70:
        return "😊"
    elif score >= 60:
        return "🙂"
    elif score >= 40:
        return "😐"
    else:
        return "😢"

def truncate_text(text, max_length=200):
    """
    Truncate text to a maximum length with ellipsis
    
    Args:
        text (str): The text to truncate
        max_length (int): Maximum length before truncation
        
    Returns:
        str: Truncated text with ellipsis if needed
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + "..."

def format_date(datetime_obj):
    """
    Format a datetime object as a readable string
    
    Args:
        datetime_obj: The datetime object to format
        
    Returns:
        str: Formatted date string
    """
    if not datetime_obj:
        return ""
    return datetime_obj.strftime("%b %d, %Y")

def format_challenge_level(level):
    """
    Format the challenge level as a readable string with emoji
    
    Args:
        level (str): The challenge level
        
    Returns:
        str: Formatted challenge level string
    """
    if level == 'easy':
        return "Easy 😊"
    elif level == 'middle':
        return "Medium 🧐"
    else:
        return "Hard 🤔"

def get_topic_display(topic, topic_type):
    """
    Format the topic display text based on topic type
    
    Args:
        topic (str): The topic (book title or author name)
        topic_type (str): The topic type ('book' or 'author')
        
    Returns:
        str: Formatted topic display text
    """
    if topic_type == 'book':
        return f'Book: "{topic}"'
    else:
        return f'Author: {topic}'