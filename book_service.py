import requests
import logging
from models import Book, db
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def search_google_books(query, max_results=10):
    """
    Search for books using the Google Books API
    
    Args:
        query (str): Search query for books
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of book dictionaries with details
    """
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}"
        response = requests.get(url)
        
        if response.status_code != 200:
            logger.error(f"Error searching Google Books API: {response.status_code}")
            return []
        
        data = response.json()
        
        if 'items' not in data:
            logger.warning(f"No books found for query: {query}")
            return []
        
        books = []
        for item in data['items']:
            volume_info = item.get('volumeInfo', {})
            
            # Extract book details
            book = {
                'title': volume_info.get('title', 'Unknown Title'),
                'authors': volume_info.get('authors', ['Unknown Author']),
                'description': volume_info.get('description', 'No description available'),
                'google_books_id': item.get('id'),
                'published_date': volume_info.get('publishedDate', 'Unknown'),
                'categories': volume_info.get('categories', []),
                'rating': volume_info.get('averageRating', 0),
                'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail', '')
            }
            
            # Get ISBN numbers if available
            industry_identifiers = volume_info.get('industryIdentifiers', [])
            for identifier in industry_identifiers:
                if identifier.get('type') == 'ISBN_13':
                    book['isbn'] = identifier.get('identifier')
                    break
                elif identifier.get('type') == 'ISBN_10':
                    book['isbn'] = identifier.get('identifier')
            
            if 'isbn' not in book:
                book['isbn'] = None
            
            books.append(book)
        
        return books
    
    except Exception as e:
        logger.error(f"Error searching Google Books API: {str(e)}")
        return []

def get_book_details(book_id):
    """
    Get detailed information about a specific book from Google Books API
    
    Args:
        book_id (str): Google Books ID
        
    Returns:
        dict: Dictionary with detailed book information
    """
    try:
        url = f"https://www.googleapis.com/books/v1/volumes/{book_id}"
        response = requests.get(url)
        
        if response.status_code != 200:
            logger.error(f"Error getting book details from Google Books API: {response.status_code}")
            return None
        
        data = response.json()
        volume_info = data.get('volumeInfo', {})
        
        # Extract and format publication year
        published_date = volume_info.get('publishedDate', '')
        publication_year = None
        if published_date and len(published_date) >= 4:
            try:
                publication_year = int(published_date[:4])
            except ValueError:
                pass
        
        # Extract primary genre/category
        categories = volume_info.get('categories', [])
        genre = categories[0] if categories else None
        
        # Create book details
        book_details = {
            'title': volume_info.get('title', 'Unknown Title'),
            'author': ', '.join(volume_info.get('authors', ['Unknown Author'])),
            'description': volume_info.get('description', 'No description available'),
            'google_books_id': data.get('id'),
            'publication_year': publication_year,
            'genre': genre,
            'isbn': None,
            'pages': volume_info.get('pageCount'),
            'language': volume_info.get('language'),
            'publisher': volume_info.get('publisher'),
            'cover_image_url': volume_info.get('imageLinks', {}).get('thumbnail', '')
        }
        
        # Get ISBN numbers if available
        industry_identifiers = volume_info.get('industryIdentifiers', [])
        for identifier in industry_identifiers:
            if identifier.get('type') == 'ISBN_13':
                book_details['isbn'] = identifier.get('identifier')
                break
            elif identifier.get('type') == 'ISBN_10':
                book_details['isbn'] = identifier.get('identifier')
        
        return book_details
    
    except Exception as e:
        logger.error(f"Error getting book details from Google Books API: {str(e)}")
        return None

def save_book_to_database(book_details):
    """
    Save book details to the database if it doesn't already exist
    
    Args:
        book_details (dict): Dictionary with book details
        
    Returns:
        Book: Book model instance
    """
    try:
        # Check if book already exists in database by Google Books ID or ISBN
        existing_book = None
        if book_details.get('google_books_id'):
            existing_book = Book.query.filter_by(google_books_id=book_details.get('google_books_id')).first()
        
        if not existing_book and book_details.get('isbn'):
            existing_book = Book.query.filter_by(isbn=book_details.get('isbn')).first()
        
        # Return existing book if found
        if existing_book:
            return existing_book
        
        # Create new book
        new_book = Book()
        new_book.title = book_details.get('title', 'Unknown Title')
        new_book.author = book_details.get('author', 'Unknown Author')
        new_book.isbn = book_details.get('isbn')
        new_book.google_books_id = book_details.get('google_books_id')
        new_book.description = book_details.get('description', '')
        new_book.publication_year = book_details.get('publication_year')
        new_book.genre = book_details.get('genre', '')
        new_book.cover_image_url = book_details.get('cover_image_url', '')
        
        db.session.add(new_book)
        db.session.commit()
        
        return new_book
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving book to database: {str(e)}")
        return None

def check_book_exists(title=None, author=None, google_books_id=None, isbn=None):
    """
    Check if a book exists in the database
    
    Args:
        title (str, optional): Book title
        author (str, optional): Book author
        google_books_id (str, optional): Google Books ID
        isbn (str, optional): ISBN number
        
    Returns:
        Book: Book model instance if found, None otherwise
    """
    try:
        # Check by Google Books ID
        if google_books_id:
            book = Book.query.filter_by(google_books_id=google_books_id).first()
            if book:
                return book
        
        # Check by ISBN
        if isbn:
            book = Book.query.filter_by(isbn=isbn).first()
            if book:
                return book
        
        # Check by title and author
        if title and author:
            book = Book.query.filter_by(title=title, author=author).first()
            if book:
                return book
        
        return None
    
    except Exception as e:
        logger.error(f"Error checking book existence: {str(e)}")
        return None

def format_book_for_quiz(book_details):
    """
    Format book details for the quiz generation
    
    Args:
        book_details (dict): Dictionary with book details
        
    Returns:
        dict: Formatted book details for quiz generation
    """
    # If book_details is a Book model instance, convert to dictionary
    if isinstance(book_details, Book):
        return {
            'title': book_details.title,
            'author': book_details.author,
            'description': book_details.description,
            'publication_year': book_details.publication_year,
            'genre': book_details.genre,
            'isbn': book_details.isbn,
            'google_books_id': book_details.google_books_id,
            'cover_image_url': book_details.cover_image_url
        }
    
    # Otherwise, return the book_details dict with consistent keys
    return {
        'title': book_details.get('title', 'Unknown Title'),
        'author': book_details.get('author', 'Unknown Author'),
        'description': book_details.get('description', 'No description available'),
        'publication_year': book_details.get('publication_year', 'Unknown'),
        'genre': book_details.get('genre', 'Unknown'),
        'isbn': book_details.get('isbn'),
        'google_books_id': book_details.get('google_books_id'),
        'cover_image_url': book_details.get('cover_image_url', '')
    }