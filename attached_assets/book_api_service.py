import os
import json
import logging
import requests
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Google Books API endpoint
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

# Open Library API endpoints
OPEN_LIBRARY_API_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVER_URL = "https://covers.openlibrary.org/b/id/{}-L.jpg"
OPEN_LIBRARY_BOOKS_API_URL = "https://openlibrary.org/api/books"
OPEN_LIBRARY_WORKS_API_URL = "https://openlibrary.org/works/{}.json"
OPEN_LIBRARY_ISBN_URL = "https://openlibrary.org/isbn/{}.json"

def get_book_info_from_google(query, limit=5):
    """
    Get book information from Google Books API.
    
    Args:
        query (str): The book title or author to search for
        limit (int): Maximum number of books to return
        
    Returns:
        list: List of dictionaries containing book information
    """
    try:
        # Format query for API
        formatted_query = quote(query)
        
        # Make API request
        response = requests.get(
            f"{GOOGLE_BOOKS_API_URL}?q={formatted_query}&maxResults={limit}"
        )
        
        if response.status_code != 200:
            logger.error(f"Google Books API error: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        
        if 'items' not in data:
            logger.info(f"No books found for: {query}")
            return []
            
        # Process and format the results
        books = []
        for item in data['items']:
            volume_info = item.get('volumeInfo', {})
            
            # Extract authors (if available)
            authors = volume_info.get('authors', ['Unknown'])
            author_string = ', '.join(authors) if isinstance(authors, list) else str(authors)
            
            # Extract categories/genres
            categories = volume_info.get('categories', ['Fiction'])
            genre_string = ', '.join(categories) if isinstance(categories, list) else str(categories)
            
            # Format description
            description = volume_info.get('description', 'No description available.')
            
            # Get cover image URL
            image_links = volume_info.get('imageLinks', {})
            cover_url = image_links.get('thumbnail', '') or image_links.get('smallThumbnail', '')
            
            book = {
                'title': volume_info.get('title', 'Unknown Title'),
                'author': author_string,
                'publication_year': volume_info.get('publishedDate', 'Unknown')[:4] if volume_info.get('publishedDate') else 'Unknown',
                'genre': genre_string,
                'description': description,
                'page_count': volume_info.get('pageCount', 0),
                'average_rating': volume_info.get('averageRating', 0),
                'rating_count': volume_info.get('ratingsCount', 0),
                'isbn': volume_info.get('industryIdentifiers', [{}])[0].get('identifier', ''),
                'publisher': volume_info.get('publisher', 'Unknown Publisher'),
                'language': volume_info.get('language', 'en'),
                'preview_link': volume_info.get('previewLink', ''),
                'cover_image': cover_url,
                'source': 'Google Books'
            }
            
            books.append(book)
        
        return books
        
    except Exception as e:
        logger.error(f"Error fetching book info from Google Books: {str(e)}")
        return []

def get_author_info_from_open_library(author_name):
    """
    Get author information from Open Library API.
    
    Args:
        author_name (str): The author name to search for
        
    Returns:
        list: List of dictionaries containing author information
    """
    try:
        # Format query for API
        formatted_query = quote(author_name)
        
        # Make API request
        response = requests.get(
            f"{OPEN_LIBRARY_API_URL}?author={formatted_query}&limit=10"
        )
        
        if response.status_code != 200:
            logger.error(f"Open Library API error: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        
        if 'docs' not in data or len(data['docs']) == 0:
            logger.info(f"No author information found for: {author_name}")
            return []
        
        # Get all unique authors from the results
        authors = {}
        for doc in data['docs']:
            if 'author_name' in doc and len(doc['author_name']) > 0:
                author_name = doc['author_name'][0]
                if author_name not in authors:
                    authors[author_name] = {
                        'name': author_name,
                        'birth_year': doc.get('author_birth_date', 'Unknown'),
                        'death_year': doc.get('author_death_date', ''),
                        'top_works': set(),
                        'subjects': set(),
                    }
                
                # Add book title to author's works
                if 'title' in doc:
                    authors[author_name]['top_works'].add(doc['title'])
                
                # Add subjects/genres
                if 'subject' in doc and isinstance(doc['subject'], list):
                    for subject in doc['subject']:
                        authors[author_name]['subjects'].add(subject)
        
        # Format author information
        author_list = []
        for author_name, info in authors.items():
            # Get author key for additional info
            author_key = None
            for doc in data['docs']:
                if 'author_name' in doc and author_name in doc['author_name']:
                    if 'author_key' in doc:
                        author_key = doc['author_key'][0]
                        break
            
            # Convert sets to lists
            notable_works = list(info['top_works'])
            subjects = list(info['subjects'])
            
            # Create biography
            biography = f"{info['name']} "
            if info['birth_year'] != 'Unknown':
                biography += f"was born in {info['birth_year']}"
                if info['death_year']:
                    biography += f" and died in {info['death_year']}"
                biography += ". "
            biography += f"Known for works such as {', '.join(notable_works[:3])}. "
            if subjects:
                biography += f"Their writing often explores themes like {', '.join(subjects[:5])}."
            
            author_info = {
                'name': info['name'],
                'birth_year': info['birth_year'],
                'death_year': info['death_year'],
                'nationality': 'Information not available',
                'biography': biography,
                'notable_works': notable_works[:10],
                'writing_style': f"Genres: {', '.join(subjects[:5])}" if subjects else "Information not available",
                'influence': "Information not available",
                'author_key': author_key,
                'source': 'Open Library'
            }
            
            author_list.append(author_info)
        
        return author_list
        
    except Exception as e:
        logger.error(f"Error fetching author info from Open Library: {str(e)}")
        return []

def search_books(query, search_type='book', limit=5):
    """
    Search for books or authors using external APIs.
    
    Args:
        query (str): The search query (book title or author name)
        search_type (str): Either 'book' or 'author'
        limit (int): Maximum number of results to return
        
    Returns:
        list: List of dictionaries containing book or author information
    """
    if search_type == 'book':
        return get_book_info_from_google(query, limit)
    else:  # author
        return get_author_info_from_open_library(query)

def get_book_details_by_isbn(isbn):
    """
    Get detailed book information from Open Library using ISBN.
    
    Args:
        isbn (str): The ISBN of the book
        
    Returns:
        dict: Dictionary containing book information from Open Library
    """
    try:
        # Clean ISBN (remove hyphens, spaces)
        clean_isbn = ''.join(c for c in isbn if c.isalnum())
        
        # Make API request
        response = requests.get(f"{OPEN_LIBRARY_ISBN_URL.format(clean_isbn)}")
        
        if response.status_code != 200:
            logger.error(f"Open Library ISBN API error: {response.status_code} - {response.text}")
            return {}
        
        data = response.json()
        
        # Get the work ID to fetch additional details
        work_id = None
        if 'works' in data and len(data['works']) > 0:
            work_id = data['works'][0]['key'].split('/')[-1]
        
        # Get cover ID if available
        cover_id = data.get('covers', [None])[0]
        cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id) if cover_id else ''
        
        # Get author information
        author_name = 'Unknown'
        if 'authors' in data and len(data['authors']) > 0:
            author_key = data['authors'][0]['key']
            author_name = data['authors'][0].get('name', 'Unknown')
            if not author_name or author_name == 'Unknown':
                # Try to get author name from key
                author_parts = author_key.split('/')
                if len(author_parts) > 0:
                    author_name = author_parts[-1].replace('_', ' ').title()
        
        # Basic book information
        book = {
            'title': data.get('title', 'Unknown Title'),
            'author': author_name,
            'publication_year': data.get('publish_date', 'Unknown')[:4] if data.get('publish_date') else 'Unknown',
            'publisher': data.get('publishers', ['Unknown Publisher'])[0] if data.get('publishers') else 'Unknown Publisher',
            'language': data.get('languages', [{'key': '/languages/eng'}])[0]['key'].split('/')[-1] if data.get('languages') else 'eng',
            'isbn': clean_isbn,
            'cover_image': cover_url,
            'work_id': work_id,
            'source': 'Open Library'
        }
        
        # If we have a work ID, get additional information
        if work_id:
            work_data = get_book_work_details(work_id)
            if work_data:
                book.update({
                    'description': work_data.get('description', 'No description available.'),
                    'subjects': work_data.get('subjects', ['Fiction']),
                    'genre': ', '.join(work_data.get('subjects', ['Fiction'])[:3]),
                    'themes': work_data.get('subjects', ['Literature'])
                })
        
        return book
        
    except Exception as e:
        logger.error(f"Error fetching book details by ISBN from Open Library: {str(e)}")
        return {}

def get_book_work_details(work_id):
    """
    Get detailed work information from Open Library.
    
    Args:
        work_id (str): The Open Library work ID
        
    Returns:
        dict: Dictionary containing work details
    """
    try:
        # Make API request
        response = requests.get(OPEN_LIBRARY_WORKS_API_URL.format(work_id))
        
        if response.status_code != 200:
            logger.error(f"Open Library Works API error: {response.status_code} - {response.text}")
            return {}
        
        data = response.json()
        
        # Extract description
        description = data.get('description', '')
        if isinstance(description, dict):
            description = description.get('value', 'No description available.')
        elif not description:
            description = 'No description available.'
            
        # Extract subjects and genres
        subjects = data.get('subjects', [])
        if not subjects and 'subject_places' in data:
            subjects.extend(data['subject_places'])
        if not subjects and 'subject_times' in data:
            subjects.extend(data['subject_times'])
        
        # Get cover ID if available
        cover_id = data.get('covers', [None])[0]
        cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id) if cover_id else ''
        
        work_details = {
            'title': data.get('title', 'Unknown Title'),
            'description': description,
            'subjects': subjects,
            'cover_image': cover_url,
            'first_publish_year': data.get('first_publish_year', 'Unknown')
        }
        
        return work_details
        
    except Exception as e:
        logger.error(f"Error fetching work details from Open Library: {str(e)}")
        return {}

def get_book_details(book_id, source='Google Books'):
    """
    Get detailed information about a specific book.
    
    Args:
        book_id (str): The book ID or ISBN
        source (str): The source API ('Google Books' or 'Open Library')
        
    Returns:
        dict: Dictionary containing detailed book information
    """
    if source == 'Google Books':
        try:
            # Make API request
            response = requests.get(f"{GOOGLE_BOOKS_API_URL}/{book_id}")
            
            if response.status_code != 200:
                logger.error(f"Google Books API error: {response.status_code} - {response.text}")
                return {}
            
            data = response.json()
            volume_info = data.get('volumeInfo', {})
            
            # Extract authors
            authors = volume_info.get('authors', ['Unknown'])
            author_string = ', '.join(authors) if isinstance(authors, list) else str(authors)
            
            # Extract categories/genres
            categories = volume_info.get('categories', ['Fiction'])
            genre_string = ', '.join(categories) if isinstance(categories, list) else str(categories)
            
            # Get cover image URL
            image_links = volume_info.get('imageLinks', {})
            cover_url = image_links.get('thumbnail', '') or image_links.get('smallThumbnail', '')
            
            # Get ISBN if available
            isbns = volume_info.get('industryIdentifiers', [])
            isbn_13 = next((item['identifier'] for item in isbns if item.get('type') == 'ISBN_13'), '')
            isbn_10 = next((item['identifier'] for item in isbns if item.get('type') == 'ISBN_10'), '')
            isbn = isbn_13 or isbn_10 or ''
            
            book = {
                'title': volume_info.get('title', 'Unknown Title'),
                'author': author_string,
                'publication_year': volume_info.get('publishedDate', 'Unknown')[:4] if volume_info.get('publishedDate') else 'Unknown',
                'genre': genre_string,
                'description': volume_info.get('description', 'No description available.'),
                'page_count': volume_info.get('pageCount', 0),
                'average_rating': volume_info.get('averageRating', 0),
                'rating_count': volume_info.get('ratingsCount', 0),
                'isbn': isbn,
                'publisher': volume_info.get('publisher', 'Unknown Publisher'),
                'language': volume_info.get('language', 'en'),
                'preview_link': volume_info.get('previewLink', ''),
                'cover_image': cover_url,
                'source': 'Google Books'
            }
            
            # If we have ISBN, try to get additional information from Open Library
            if isbn:
                ol_book = get_book_details_by_isbn(isbn)
                if ol_book:
                    # Merge information, prioritizing Google Books for overlapping fields
                    # but using Open Library for fields that Google Books doesn't have
                    for key, value in ol_book.items():
                        if key not in book or not book[key] or book[key] == 'Unknown' or book[key] == 'No description available.':
                            book[key] = value
                    
                    # Add a note that this is from multiple sources
                    book['source'] = 'Google Books + Open Library'
            
            return book
            
        except Exception as e:
            logger.error(f"Error fetching book details from Google Books: {str(e)}")
            return {}
    
    elif source == 'Open Library' and book_id.isdigit():
        # Assume book_id is a work ID
        return get_book_work_details(book_id)
    
    elif source == 'Open Library':
        # Assume book_id is an ISBN
        return get_book_details_by_isbn(book_id)
    
    return {}

def format_book_for_quiz(book):
    """
    Format a book dictionary from external APIs to match the format expected by quiz generation.
    
    Args:
        book (dict): Book information from external API
        
    Returns:
        dict: Formatted book data for quiz generation
    """
    return {
        'title': book.get('title', 'Unknown Title'),
        'author': book.get('author', 'Unknown Author'),
        'publication_year': book.get('publication_year', 'Unknown'),
        'genre': book.get('genre', 'Fiction'),
        'description': book.get('description', 'No description available.'),
        'themes': book.get('themes', ['Literature']),
        'key_characters': book.get('key_characters', ['Information not available']),
        'awards': book.get('awards', ['Information not available']),
        'cover_image': book.get('cover_image', '')
    }

def format_author_for_quiz(author):
    """
    Format an author dictionary from external APIs to match the format expected by quiz generation.
    
    Args:
        author (dict): Author information from external API
        
    Returns:
        dict: Formatted author data for quiz generation
    """
    return {
        'name': author.get('name', 'Unknown'),
        'birth_year': author.get('birth_year', 'Unknown'),
        'death_year': author.get('death_year', ''),
        'nationality': author.get('nationality', 'Unknown'),
        'biography': author.get('biography', 'No biography available.'),
        'notable_works': author.get('notable_works', ['Information not available']),
        'writing_style': author.get('writing_style', 'Information not available'),
        'influence': author.get('influence', 'Information not available')
    }

def get_book_recommendations(book_title=None, author=None, genre=None, limit=5):
    """
    Get book recommendations based on book title, author, or genre.
    
    Args:
        book_title (str, optional): Title of a book to find similar books
        author (str, optional): Author name to find books by the same author
        genre (str, optional): Genre to find books in the same category
        limit (int): Maximum number of recommendations to return
        
    Returns:
        list: List of recommended book dictionaries
    """
    try:
        recommendations = []
        
        # If we have an author name, get books by that author
        if author:
            logger.info(f"Finding books by author: {author}")
            query = f"author:{author}"
            response = requests.get(f"{OPEN_LIBRARY_API_URL}?q={quote(query)}&limit={limit}")
            
            if response.status_code == 200:
                data = response.json()
                if 'docs' in data and len(data['docs']) > 0:
                    for doc in data['docs'][:limit]:
                        # Get cover ID if available
                        cover_id = doc.get('cover_i')
                        cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id) if cover_id else ''
                        
                        book = {
                            'title': doc.get('title', 'Unknown Title'),
                            'author': doc.get('author_name', ['Unknown Author'])[0] if doc.get('author_name') else 'Unknown Author',
                            'publication_year': str(doc.get('first_publish_year', 'Unknown')),
                            'cover_image': cover_url,
                            'source': 'Open Library'
                        }
                        
                        # Add ISBN if available
                        if 'isbn' in doc and len(doc['isbn']) > 0:
                            book['isbn'] = doc['isbn'][0]
                        
                        recommendations.append(book)
        
        # If we have a genre, get books in that genre
        elif genre:
            logger.info(f"Finding books in genre: {genre}")
            query = f"subject:{genre}"
            response = requests.get(f"{OPEN_LIBRARY_API_URL}?q={quote(query)}&limit={limit}")
            
            if response.status_code == 200:
                data = response.json()
                if 'docs' in data and len(data['docs']) > 0:
                    for doc in data['docs'][:limit]:
                        # Get cover ID if available
                        cover_id = doc.get('cover_i')
                        cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id) if cover_id else ''
                        
                        book = {
                            'title': doc.get('title', 'Unknown Title'),
                            'author': doc.get('author_name', ['Unknown Author'])[0] if doc.get('author_name') else 'Unknown Author',
                            'publication_year': str(doc.get('first_publish_year', 'Unknown')),
                            'cover_image': cover_url,
                            'source': 'Open Library'
                        }
                        
                        # Add ISBN if available
                        if 'isbn' in doc and len(doc['isbn']) > 0:
                            book['isbn'] = doc['isbn'][0]
                        
                        recommendations.append(book)
        
        # If we have a book title, try to find similar books
        elif book_title:
            logger.info(f"Finding books similar to: {book_title}")
            # First, search for the book to get its details
            book_results = get_book_info_from_google(book_title, 1)
            
            if book_results:
                book = book_results[0]
                # Use the author and genre to find similar books
                author_books = []
                genre_books = []
                
                if book.get('author'):
                    author_query = f"author:{book['author'].split(',')[0]}"  # Use the first author
                    response = requests.get(f"{OPEN_LIBRARY_API_URL}?q={quote(author_query)}&limit={limit}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'docs' in data and len(data['docs']) > 0:
                            for doc in data['docs'][:limit]:
                                if doc.get('title') != book_title:  # Don't include the original book
                                    # Get cover ID if available
                                    cover_id = doc.get('cover_i')
                                    cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id) if cover_id else ''
                                    
                                    book_item = {
                                        'title': doc.get('title', 'Unknown Title'),
                                        'author': doc.get('author_name', ['Unknown Author'])[0] if doc.get('author_name') else 'Unknown Author',
                                        'publication_year': str(doc.get('first_publish_year', 'Unknown')),
                                        'cover_image': cover_url,
                                        'source': 'Open Library'
                                    }
                                    
                                    # Add ISBN if available
                                    if 'isbn' in doc and len(doc['isbn']) > 0:
                                        book_item['isbn'] = doc['isbn'][0]
                                    
                                    author_books.append(book_item)
                
                if book.get('genre'):
                    # Extract first genre
                    first_genre = book['genre'].split(',')[0].strip()
                    genre_query = f"subject:{first_genre}"
                    response = requests.get(f"{OPEN_LIBRARY_API_URL}?q={quote(genre_query)}&limit={limit}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'docs' in data and len(data['docs']) > 0:
                            for doc in data['docs'][:limit]:
                                if doc.get('title') != book_title:  # Don't include the original book
                                    # Get cover ID if available
                                    cover_id = doc.get('cover_i')
                                    cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id) if cover_id else ''
                                    
                                    book_item = {
                                        'title': doc.get('title', 'Unknown Title'),
                                        'author': doc.get('author_name', ['Unknown Author'])[0] if doc.get('author_name') else 'Unknown Author',
                                        'publication_year': str(doc.get('first_publish_year', 'Unknown')),
                                        'cover_image': cover_url,
                                        'source': 'Open Library'
                                    }
                                    
                                    # Add ISBN if available
                                    if 'isbn' in doc and len(doc['isbn']) > 0:
                                        book_item['isbn'] = doc['isbn'][0]
                                    
                                    genre_books.append(book_item)
                
                # Combine results from both author and genre, prioritizing author matches
                recommendations.extend(author_books[:3])
                
                # Add genre matches, avoiding duplicates
                for book_item in genre_books:
                    if len(recommendations) < limit:
                        # Check if this book is already in recommendations
                        if not any(b.get('title') == book_item.get('title') for b in recommendations):
                            recommendations.append(book_item)
        
        # If we still don't have enough recommendations, get popular books
        if not recommendations:
            logger.info("Using popular books as recommendations")
            # Get a mix of classic and modern literature
            popular_subjects = ['fiction', 'fantasy', 'science_fiction', 'romance', 'mystery']
            
            for subject in popular_subjects:
                if len(recommendations) < limit:
                    query = f"subject:{subject}"
                    response = requests.get(f"{OPEN_LIBRARY_API_URL}?q={quote(query)}&limit=3")
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'docs' in data and len(data['docs']) > 0:
                            for doc in data['docs'][:1]:  # Just take 1 book per genre for diversity
                                # Get cover ID if available
                                cover_id = doc.get('cover_i')
                                cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id) if cover_id else ''
                                
                                book = {
                                    'title': doc.get('title', 'Unknown Title'),
                                    'author': doc.get('author_name', ['Unknown Author'])[0] if doc.get('author_name') else 'Unknown Author',
                                    'publication_year': str(doc.get('first_publish_year', 'Unknown')),
                                    'cover_image': cover_url,
                                    'source': 'Open Library'
                                }
                                
                                # Add ISBN if available
                                if 'isbn' in doc and len(doc['isbn']) > 0:
                                    book['isbn'] = doc['isbn'][0]
                                
                                recommendations.append(book)
        
        # Ensure we return at most 'limit' recommendations
        return recommendations[:limit]
        
    except Exception as e:
        logger.error(f"Error getting book recommendations: {str(e)}")
        return []