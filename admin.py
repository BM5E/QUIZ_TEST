from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Book, APIKey, StoredQuestion, db
from ai_service_manager import AIServiceManager
from ai_quiz_service import generate_comprehensive_question_set, save_questions_to_database
from book_service import get_book_details, save_book_to_database
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Blueprint
admin = Blueprint('admin', __name__)

# API Keys management route
@admin.route('/api-keys', methods=['GET', 'POST'])
@login_required
def api_keys():
    """Manage AI service API keys"""
    if request.method == 'POST':
        api_name = request.form.get('api_name')
        api_key = request.form.get('api_key')
        description = request.form.get('description')
        priority = request.form.get('priority', 1)
        
        if not api_name or not api_key:
            flash('API name and key are required.', 'danger')
        else:
            # Try to convert priority to int
            try:
                priority = int(priority)
            except ValueError:
                priority = 1
            
            # Add the API key
            if AIServiceManager.add_api_key(api_name, api_key, description, priority):
                flash(f'API key for {api_name} added successfully.', 'success')
            else:
                flash('Failed to add API key.', 'danger')
    
    # Get all API keys
    api_keys = AIServiceManager.get_all_api_keys()
    
    return render_template('admin/api_keys.html', api_keys=api_keys)

# Deactivate API key route
@admin.route('/api-keys/deactivate/<int:key_id>', methods=['POST'])
@login_required
def deactivate_api_key(key_id):
    """Deactivate an API key"""
    key = APIKey.query.get_or_404(key_id)
    key.is_active = False
    db.session.commit()
    flash(f'API key for {key.api_name} deactivated.', 'success')
    return redirect(url_for('admin.api_keys'))

# Activate API key route
@admin.route('/api-keys/activate/<int:key_id>', methods=['POST'])
@login_required
def activate_api_key(key_id):
    """Activate an API key"""
    key = APIKey.query.get_or_404(key_id)
    key.is_active = True
    db.session.commit()
    flash(f'API key for {key.api_name} activated.', 'success')
    return redirect(url_for('admin.api_keys'))

# Delete API key route
@admin.route('/api-keys/delete/<int:key_id>', methods=['POST'])
@login_required
def delete_api_key(key_id):
    """Delete an API key"""
    key = APIKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    flash(f'API key for {key.api_name} deleted.', 'success')
    return redirect(url_for('admin.api_keys'))

# Book management route
@admin.route('/books')
@login_required
def books():
    """Manage books in the database"""
    books = Book.query.order_by(Book.title).all()
    return render_template('admin/books.html', books=books)

# Book details route
@admin.route('/books/<int:book_id>')
@login_required
def book_details(book_id):
    """View book details and question statistics"""
    book = Book.query.get_or_404(book_id)
    
    # Count questions by type and difficulty
    question_stats = {}
    for q_type in ['choice', 'blank']:
        question_stats[q_type] = {}
        for difficulty in ['easy', 'middle', 'hard']:
            count = StoredQuestion.query.filter_by(
                book_id=book.id,
                question_type=q_type,
                difficulty=difficulty
            ).count()
            question_stats[q_type][difficulty] = count
    
    return render_template(
        'admin/book_details.html',
        book=book,
        question_stats=question_stats
    )

# Generate comprehensive question set route
@admin.route('/books/generate-questions/<int:book_id>', methods=['GET', 'POST'])
@login_required
def generate_questions(book_id):
    """Generate a comprehensive set of questions for a book"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        try:
            # Generate comprehensive question set (198 questions)
            questions = generate_comprehensive_question_set(book)
            
            if questions:
                # Save questions to database
                saved_count = save_questions_to_database(book.id, questions)
                flash(f'Successfully generated and saved {saved_count} questions for "{book.title}".', 'success')
            else:
                flash('Failed to generate questions. No active AI service available.', 'danger')
            
            return redirect(url_for('admin.book_details', book_id=book.id))
        
        except Exception as e:
            logger.error(f"Error generating comprehensive question set: {str(e)}")
            flash('An error occurred while generating questions. Please check API keys and try again.', 'danger')
    
    return render_template('admin/generate_questions.html', book=book)

# Add book from Google Books route
@admin.route('/books/add', methods=['GET', 'POST'])
@login_required
def add_book():
    """Add a book from Google Books to the database"""
    from book_service import search_google_books
    
    results = []
    search_performed = False
    
    if request.method == 'POST':
        query = request.form.get('query')
        
        if query:
            try:
                # Search Google Books
                results = search_google_books(query)
                search_performed = True
                
                # Check if add_book_id is in form (from search results)
                add_book_id = request.form.get('add_book_id')
                if add_book_id:
                    # Get book details and save to database
                    book_details = get_book_details(add_book_id)
                    if book_details:
                        book = save_book_to_database(book_details)
                        if book:
                            flash(f'Book "{book.title}" successfully added to database.', 'success')
                            return redirect(url_for('admin.book_details', book_id=book.id))
                        else:
                            flash('Failed to save book to database.', 'danger')
                    else:
                        flash('Failed to get book details from Google Books.', 'danger')
            
            except Exception as e:
                logger.error(f"Error in add book: {str(e)}")
                flash('An error occurred while searching for books. Please try again.', 'danger')
    
    return render_template('admin/add_book.html', results=results, search_performed=search_performed)