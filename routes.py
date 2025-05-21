from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User, Quiz
from db import db
from utils import truncate_text, format_score
from openai_service import get_book_or_author_info
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Blueprint
main = Blueprint('main', __name__)

# Home page route
@main.route('/')
def index():
    """Render the home page"""
    return render_template('index.html')

# Dashboard route
@main.route('/dashboard')
@login_required
def dashboard():
    """Render the user dashboard with quiz history and recommendations"""
    # Get user's recent quizzes (limit to 5 for performance)
    recent_quizzes = Quiz.query.filter_by(
        user_id=current_user.id
    ).order_by(Quiz.created_at.desc()).limit(5).all()
    
    # Simplified dashboard with just quiz history
    
    return render_template(
        'dashboard.html',
        user=current_user,
        recent_quizzes=recent_quizzes,
        truncate_text=truncate_text,
        format_score=format_score
    )

# Search route
@main.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Search for books and authors using Google Books API or AI service"""
    from forms import SearchForm
    from book_service import search_google_books
    
    form = SearchForm()
    results = []
    search_performed = False
    
    if form.validate_on_submit():
        query = form.query.data
        search_type = form.search_type.data
        
        try:
            if search_type == 'book':
                # First try Google Books API for accurate book information
                google_results = search_google_books(query)
                
                if google_results:
                    # Convert Google Books results to a consistent format
                    results = []
                    for book in google_results:
                        results.append({
                            'title': book.get('title', 'Unknown Title'),
                            'author': ', '.join(book.get('authors', ['Unknown Author'])),
                            'description': book.get('description', 'No description available'),
                            'publication_year': book.get('published_date', 'Unknown')[:4] if book.get('published_date') else 'Unknown',
                            'genre': ', '.join(book.get('categories', ['Unknown'])) if book.get('categories') else 'Unknown',
                            'google_books_id': book.get('google_books_id'),
                            'thumbnail': book.get('thumbnail', '')
                        })
                else:
                    # Fallback to AI-generated information if Google Books API fails
                    results = get_book_or_author_info(query, 'book')
            else:
                # Author search still uses AI service
                results = get_book_or_author_info(query, 'author')
            
            search_performed = True
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            flash('An error occurred during search. Please try again.', 'danger')
    
    return render_template(
        'search.html',
        form=form,
        results=results,
        search_performed=search_performed,
        truncate_text=truncate_text,
        search_type=form.search_type.data if form.validate_on_submit() else 'book'
    )

# Book info route
@main.route('/book/<book_title>')
@login_required
def book_info(book_title):
    """Display detailed information about a book"""
    from book_service import search_google_books
    
    # Try to find the book with Google Books API
    results = search_google_books(book_title, max_results=1)
    if results:
        book = results[0]
        book_data = {
            'title': book.get('title', 'Unknown Title'),
            'author': ', '.join(book.get('authors', ['Unknown Author'])),
            'description': book.get('description', 'No description available'),
            'publication_year': book.get('published_date', 'Unknown')[:4] if book.get('published_date') else 'Unknown',
            'genre': ', '.join(book.get('categories', ['Unknown'])) if book.get('categories') else 'Unknown',
            'google_books_id': book.get('google_books_id'),
            'cover_image_url': book.get('thumbnail', '')
        }
    else:
        # Fall back to AI-generated information
        book_info = get_book_or_author_info(book_title, 'book')
        book_data = book_info[0] if book_info else None
    
    if not book_data:
        flash('Book not found.', 'danger')
        return redirect(url_for('main.search'))
    
    return render_template(
        'book_info.html',
        book=book_data
    )

# Author info route
@main.route('/author/<author_name>')
@login_required
def author_info(author_name):
    """Display detailed information about an author"""
    author = get_author_info(author_name)
    if not author:
        flash('Author not found.', 'danger')
        return redirect(url_for('main.search'))
    
    return render_template(
        'author_info.html',
        author=author
    )

# User profile route
@main.route('/profile')
@login_required
def profile():
    """Display user profile information"""
    # Get all user's quizzes
    quizzes = Quiz.query.filter_by(
        user_id=current_user.id
    ).order_by(Quiz.created_at.desc()).all()
    
    # Get all user's achievements
    achievements = Achievement.query.filter_by(
        user_id=current_user.id
    ).order_by(Achievement.achieved_at.desc()).all()
    
    return render_template(
        'profile.html',
        user=current_user,
        quizzes=quizzes,
        achievements=achievements,
        truncate_text=truncate_text,
        format_score=format_score
    )

# Shared content view route
@main.route('/shared/<share_key>')
def view_shared(share_key):
    """View shared quiz results or achievements"""
    shared_content, content, user = get_shared_content(share_key)
    
    if not shared_content or not content or not user:
        flash('The shared content is no longer available.', 'danger')
        return redirect(url_for('main.index'))
    
    return render_template(
        'shared.html',
        shared_content=shared_content,
        content=content,
        user=user,
        content_type=shared_content.content_type,
        truncate_text=truncate_text,
        format_score=format_score
    )

# Error handlers
@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_message="Page Not Found"), 404

@main.app_errorhandler(500)
def server_error(e):
    return render_template('error.html', error_code=500, error_message="Internal Server Error"), 500

# Import OpenAI service (only needed for routes)
from openai_service import get_book_or_author_info
