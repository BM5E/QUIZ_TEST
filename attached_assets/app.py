import os
import logging
import json
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from db import db
import openai_service
from openai_service import generate_quiz_questions, get_fallback_quiz_questions
import ad_manager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "your-secret-key"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize CSRF Protection
csrf = CSRFProtect()
csrf.init_app(app)

# Import models after initializing db to avoid circular imports
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    from models import User, Quiz, QuizQuestion, UserAnswer, Achievement
    db.create_all()
    
# Import other modules that depend on models
import achievement_utils

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    from forms import RegistrationForm
    from models import User
    
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))
        
        # Create new user
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Log in the new user
        login_user(new_user)
        flash('Registration successful! Welcome to BookQuiz.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    from forms import LoginForm
    from models import User
    
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Login successful!', 'success')
            
            # Get next page from query parameter
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('profile'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    from models import Quiz, Achievement
    
    # Get the user's quizzes and achievements
    quizzes = Quiz.query.filter_by(user_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    achievements = Achievement.query.filter_by(user_id=current_user.id).order_by(Achievement.achieved_at.desc()).all()
    
    # Create a unified timeline of activities
    timeline = []
    
    for quiz in quizzes:
        timeline.append({
            'type': 'quiz',
            'data': quiz,
            'date': quiz.created_at
        })
    
    for achievement in achievements:
        timeline.append({
            'type': 'achievement',
            'data': achievement,
            'date': achievement.achieved_at
        })
    
    # Sort timeline by date (newest first)
    timeline.sort(key=lambda x: x['date'], reverse=True)
    
    # Get book recommendations based on user's quiz history
    from recommendation_service import generate_recommendations_for_user
    recommendations = generate_recommendations_for_user(current_user, num_recommendations=3)
    
    return render_template(
        'profile.html', 
        timeline=timeline, 
        quizzes=quizzes, 
        achievements=achievements,
        recommendations=recommendations,
        achievement_utils=achievement_utils
    )

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    from forms import SearchForm
    import logging
    import book_api_service
    
    logger = logging.getLogger(__name__)
    form = SearchForm()
    results = []
    
    if form.validate_on_submit() or request.args.get('query'):
        query = form.query.data if form.validate_on_submit() else request.args.get('query')
        search_type = form.search_type.data if form.validate_on_submit() else request.args.get('search_type', 'book')
        use_api = request.args.get('use_api', 'true').lower() == 'true'
        
        try:
            # Try using the external book API first
            if use_api:
                results = book_api_service.search_books(query, search_type)
                
                # If API results are empty, fall back to OpenAI
                if not results:
                    logger.info(f"No results from external API for {search_type}: {query}. Falling back to OpenAI.")
                    results = openai_service.get_book_or_author_info(query, search_type)
                else:
                    logger.info(f"Found {len(results)} results from external API for {search_type}: {query}")
                    # Set source in the session for tracking where data comes from
                    session['data_source'] = 'external_api'
            else:
                # Use OpenAI directly if API is disabled
                results = openai_service.get_book_or_author_info(query, search_type)
                session['data_source'] = 'openai'
            
            # Check if OpenAI results contain the temporary unavailability message
            if session.get('data_source') == 'openai' and results and len(results) > 0:
                first_result = results[0]
                if search_type == 'book' and 'temporarily unavailable' in first_result.get('description', ''):
                    flash('The OpenAI service is experiencing high traffic. Showing limited results.', 'warning')
                elif search_type == 'author' and 'temporarily unavailable' in first_result.get('biography', ''):
                    flash('The OpenAI service is experiencing high traffic. Showing limited results.', 'warning')
            
            if not results:
                flash(f'No {search_type}s found matching "{query}".', 'warning')
                
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            flash(f'An error occurred while searching. Please try again later.', 'danger')
            results = []
    
    return render_template('search.html', form=form, results=results, search_type=search_type if 'search_type' in locals() else 'book')

@app.route('/book_summary/<topic>/<topic_type>')
@login_required
def book_summary(topic, topic_type):
    """
    Display a detailed summary of the book/author before proceeding to the quiz.
    This provides users with more context and information about the book or author.
    """
    import book_api_service
    
    # Store the quiz topic in session for use in quiz creation
    session['quiz_topic'] = topic
    session['quiz_topic_type'] = topic_type
    
    # Determine data source - use the same as search unless explicitly overridden
    use_api = request.args.get('use_api', 'true').lower() == 'true'
    data_source = request.args.get('source', session.get('data_source', 'external_api'))
    
    # Get detailed information about the book or author
    try:
        if data_source == 'external_api' and use_api:
            # Try external API first
            results = book_api_service.search_books(topic, topic_type)
            
            # If API results are empty, fall back to OpenAI
            if not results:
                app.logger.info(f"No results from external API for {topic_type}: {topic}. Falling back to OpenAI.")
                results = openai_service.get_book_or_author_info(topic, topic_type)
                data_source = 'openai'
            else:
                app.logger.info(f"Found {len(results)} results from external API for {topic_type}: {topic}")
        else:
            # Use OpenAI directly if API is disabled or was previously used
            results = openai_service.get_book_or_author_info(topic, topic_type)
            data_source = 'openai'
        
        if not results or len(results) == 0:
            flash(f'No information found for {topic_type} "{topic}".', 'warning')
            return redirect(url_for('search'))
        
        # Use the first result
        info = results[0]
        
        # Add the data source to the info dictionary
        info['data_source'] = data_source
        
        # Check if OpenAI results contain the temporary unavailability message
        if data_source == 'openai':
            if topic_type == 'book' and 'temporarily unavailable' in info.get('description', ''):
                flash('The OpenAI service is experiencing high traffic. Showing limited information.', 'warning')
            elif topic_type == 'author' and 'temporarily unavailable' in info.get('biography', ''):
                flash('The OpenAI service is experiencing high traffic. Showing limited information.', 'warning')
        else:
            # Add a message to indicate data is from external API
            flash('Showing information from external book sources.', 'info')
        
        return render_template('book_summary.html', info=info, topic=topic, topic_type=topic_type)
    
    except Exception as e:
        app.logger.error(f"Error getting book/author summary: {str(e)}")
        flash(f'An error occurred while retrieving information. Please try again later.', 'danger')
        return redirect(url_for('search'))

@app.route('/quiz_settings')
@login_required
def quiz_settings():
    from forms import QuizForm
    
    # Get the topic from session
    topic = session.get('quiz_topic')
    topic_type = session.get('quiz_topic_type')
    
    if not topic or not topic_type:
        flash('Please select a book or author first', 'warning')
        return redirect(url_for('search'))
    
    form = QuizForm()
    return render_template('quiz_settings.html', form=form, topic=topic, topic_type=topic_type)

@app.route('/create_quiz')
@login_required
def create_quiz():
    from models import Quiz, QuizQuestion
    
    # Get quiz parameters
    book_or_author = session.get('quiz_topic')
    search_type = session.get('quiz_topic_type')
    num_questions = request.args.get('num_questions', 5, type=int)
    challenge_level = request.args.get('challenge_level', 'middle')
    question_type = request.args.get('question_type', 'choice')
    
    if not book_or_author:
        flash('Please select a book or author first', 'warning')
        return redirect(url_for('search'))
    
    try:
        # Find previous attempts for this topic by the user
        previous_attempts = Quiz.query.filter_by(
            user_id=current_user.id,
            topic=book_or_author,
            topic_type=search_type
        ).count()
        
        # Create a new quiz with attempt number
        new_quiz = Quiz(
            user_id=current_user.id,
            title=f"Quiz on {book_or_author}",
            topic=book_or_author,
            topic_type=search_type,
            challenge_level=challenge_level,
            question_type=question_type,
            total_questions=num_questions,
            attempt_number=previous_attempts + 1
        )
        db.session.add(new_quiz)
        db.session.flush()  # Get the quiz ID without committing
        
        # Generate questions using OpenAI (handle API limits)
        try:
            questions = generate_quiz_questions(book_or_author, search_type, num_questions=num_questions, 
                                             challenge_level=challenge_level, question_type=question_type)
            if not questions:
                raise Exception("Failed to generate questions")
        except Exception as e:
            logging.error(f"Error generating quiz questions: {str(e)}")
            flash(f"We encountered an API limit. Using our curated questions instead.", "warning")
            # Use fallback questions when API fails
            questions = get_fallback_quiz_questions(
                book_or_author, 
                search_type, 
                num_questions=num_questions, 
                question_type=question_type
            )
        
        # Save questions to database
        for q in questions:
            if q.get('question_type', 'choice') == 'choice':
                question = QuizQuestion(
                    quiz_id=new_quiz.id,
                    question_text=q['question'],
                    question_type='choice',
                    correct_answer=q['correct_answer'],
                    option_a=q['options'][0],
                    option_b=q['options'][1],
                    option_c=q['options'][2],
                    option_d=q['options'][3]
                )
            else:
                # For fill-in-the-blank questions
                question = QuizQuestion(
                    quiz_id=new_quiz.id,
                    question_text=q['question'],
                    question_type='blank',
                    correct_answer=q['correct_answer']
                )
            db.session.add(question)
        
        db.session.commit()
        
        # Clear session data
        session.pop('quiz_topic', None)
        session.pop('quiz_topic_type', None)
        
        # Redirect to take the quiz
        return redirect(url_for('take_quiz', quiz_id=new_quiz.id))
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating quiz: {str(e)}")
        flash('Failed to create quiz. Please try again.', 'danger')
        return redirect(url_for('search'))

@app.route('/quiz/<int:quiz_id>')
@login_required
def take_quiz(quiz_id):
    from models import Quiz, QuizQuestion
    
    # Get the quiz and verify ownership
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz.user_id != current_user.id:
        flash('Unauthorized access to quiz.', 'danger')
        return redirect(url_for('profile'))
    
    # Check if quiz is already completed
    if quiz.is_completed:
        flash('This quiz has already been completed.', 'info')
        return redirect(url_for('quiz_results', quiz_id=quiz_id))
    
    # Get questions for the quiz
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
    
    if not questions:
        flash('No questions found for this quiz.', 'warning')
        return redirect(url_for('profile'))
    
    # Create a simple form for CSRF protection
    from flask_wtf import FlaskForm
    form = FlaskForm()
    
    return render_template('quiz.html', quiz=quiz, questions=questions, form=form)

@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    from models import Quiz, QuizQuestion, UserAnswer
    
    # Get the quiz and verify ownership
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz.user_id != current_user.id:
        flash('Unauthorized access to quiz.', 'danger')
        return redirect(url_for('profile'))
    
    if quiz.is_completed:
        flash('This quiz has already been completed.', 'info')
        return redirect(url_for('quiz_results', quiz_id=quiz_id))
    
    # Get all questions for the quiz
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
    
    # Process user answers
    correct_count = 0
    
    try:
        for question in questions:
            answer_key = f'question_{question.id}'
            user_answer = request.form.get(answer_key, '').strip()
            
            # Check if answer is correct
            is_correct = False
            
            if question.question_type == 'choice':
                is_correct = user_answer == question.correct_answer
            else:  # fill-in-the-blank
                # Compare case-insensitive
                is_correct = user_answer.lower() == question.correct_answer.lower()
            
            if is_correct:
                correct_count += 1
            
            # Save user's answer
            answer = UserAnswer(
                quiz_id=quiz_id,
                question_id=question.id,
                user_answer=user_answer,
                is_correct=is_correct
            )
            db.session.add(answer)
        
        # Update quiz statistics
        quiz.correct_answers = correct_count
        quiz.score = (correct_count / quiz.total_questions) * 100
        quiz.is_completed = True
        quiz.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Check for achievements
        achievement_utils.check_achievements(current_user.id, quiz, db.session)
        
        return redirect(url_for('quiz_results', quiz_id=quiz_id))
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error submitting quiz: {str(e)}")
        flash('An error occurred while submitting your quiz. Please try again.', 'danger')
        return redirect(url_for('take_quiz', quiz_id=quiz_id))

@app.route('/quiz_results/<int:quiz_id>')
@login_required
def quiz_results(quiz_id):
    from models import Quiz, QuizQuestion, UserAnswer
    from book_api_service import get_book_recommendations
    
    # Get the quiz and verify ownership
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz.user_id != current_user.id:
        flash('Unauthorized access to quiz results.', 'danger')
        return redirect(url_for('profile'))
    
    # Get questions and user answers
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
    user_answers = UserAnswer.query.filter_by(quiz_id=quiz_id).all()
    
    # Create a dictionary of user answers for easy lookup
    answers_dict = {answer.question_id: answer for answer in user_answers}
    
    # Get book recommendations based on the quiz topic
    recommendations = []
    if quiz.topic_type == 'book':
        # Get recommendations based on book title
        recommendations = get_book_recommendations(book_title=quiz.topic, limit=3)
    elif quiz.topic_type == 'author':
        # Get recommendations based on author name
        recommendations = get_book_recommendations(author=quiz.topic, limit=3)
    
    return render_template('quiz_results.html', 
                           quiz=quiz, 
                           questions=questions, 
                           answers=answers_dict,
                           recommendations=recommendations)

@app.route('/quiz_history')
@login_required
def quiz_history():
    from models import Quiz
    
    # Get all completed quizzes for the user
    quizzes = Quiz.query.filter_by(
        user_id=current_user.id, 
        is_completed=True
    ).order_by(Quiz.completed_at.desc()).all()
    
    return render_template('quiz_history.html', quizzes=quizzes)

# Social sharing routes
@app.route('/share/quiz/<int:quiz_id>')
@login_required
def share_quiz(quiz_id):
    """
    Create a shareable link for a quiz and return the share URL.
    """
    from models import Quiz
    import social_utils
    
    # Get the quiz and verify ownership
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz.user_id != current_user.id:
        flash('You can only share your own quizzes.', 'danger')
        return redirect(url_for('profile'))
    
    # Create shared content entry
    shared_content = social_utils.create_shared_content(current_user.id, 'quiz', quiz_id)
    
    # Get the absolute share URL
    share_url = social_utils.get_absolute_share_url(shared_content.share_key)
    
    # Get social media share links
    title = f"Check out my quiz on {quiz.topic}!"
    description = f"{current_user.username} scored {quiz.score:.0f}% on this BookQuiz about {quiz.topic}."
    social_links = social_utils.get_social_share_links(share_url, title, description)
    
    return render_template('share.html', 
                          content_type='quiz',
                          content=quiz,
                          share_url=share_url,
                          social_links=social_links)

@app.route('/share/achievement/<int:achievement_id>')
@login_required
def share_achievement(achievement_id):
    """
    Create a shareable link for an achievement and return the share URL.
    """
    from models import Achievement
    import social_utils
    
    # Get the achievement and verify ownership
    achievement = Achievement.query.get_or_404(achievement_id)
    
    if achievement.user_id != current_user.id:
        flash('You can only share your own achievements.', 'danger')
        return redirect(url_for('profile'))
    
    # Create shared content entry
    shared_content = social_utils.create_shared_content(current_user.id, 'achievement', achievement_id)
    
    # Get the absolute share URL
    share_url = social_utils.get_absolute_share_url(shared_content.share_key)
    
    # Get social media share links
    title = f"I earned the '{achievement.name}' achievement on BookQuiz!"
    description = f"{current_user.username} earned the {achievement.name} achievement: {achievement.description}"
    social_links = social_utils.get_social_share_links(share_url, title, description)
    
    return render_template('share.html', 
                          content_type='achievement',
                          content=achievement,
                          share_url=share_url,
                          social_links=social_links)

@app.route('/s/<share_key>')
def view_shared(share_key):
    """
    View shared content based on share key.
    """
    import social_utils
    from models import Quiz, Achievement
    
    # Get shared content info
    shared_content, content, creator = social_utils.get_shared_content(share_key)
    
    if not shared_content or not content or not creator:
        flash('This shared content is no longer available.', 'warning')
        return redirect(url_for('index'))
    
    if shared_content.content_type == 'quiz':
        # Get questions and user answers for the quiz
        from models import QuizQuestion, UserAnswer
        questions = QuizQuestion.query.filter_by(quiz_id=content.id).all()
        user_answers = UserAnswer.query.filter_by(quiz_id=content.id).all()
        answers_dict = {answer.question_id: answer for answer in user_answers}
        
        return render_template('shared_quiz.html', 
                              shared=shared_content,
                              quiz=content, 
                              questions=questions,
                              answers=answers_dict,
                              creator=creator)
    
    elif shared_content.content_type == 'achievement':
        return render_template('shared_achievement.html', 
                              shared=shared_content,
                              achievement=content,
                              creator=creator)
    
    # If content type is not recognized
    flash('Invalid content type.', 'warning')
    return redirect(url_for('index'))

# Ad Management Routes
@app.route('/api/ad-config')
def get_ad_config():
    """
    Get the current ad configuration for the client-side ad service.
    This provides configuration information about which ad placements are active,
    the user's ad preferences, and general ad settings.
    """
    config = ad_manager.get_ad_config()
    
    # Only send necessary information to the client
    client_config = {
        'enabled': config['enabled'],
        'userOptOut': config['userOptOut'],
        'testMode': config['test_mode'],
        'refreshInterval': config['refreshInterval'],
        'maxAdsPerPage': config['maxAdsPerPage'],
        'placements': config['placements'],
        'adNetwork': config['adNetwork']
    }
    
    return jsonify(client_config)

@app.route('/api/ad-preferences', methods=['POST'])
@login_required
def update_ad_preferences():
    """
    Update a user's ad preferences.
    Allows users to opt in or out of seeing ads throughout the application.
    """
    try:
        data = request.get_json()
        if 'enabled' not in data:
            return jsonify({'success': False, 'error': 'Missing enabled parameter'}), 400
        
        # Toggle the user's ad preferences
        success = ad_manager.toggle_user_ad_preference(current_user.id, data['enabled'])
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update preferences'}), 500
    
    except Exception as e:
        app.logger.error(f"Error updating ad preferences: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/user-preferences')
@login_required
def user_preferences():
    """
    User preferences page where users can manage account settings including ad preferences.
    """
    # Get user's ad preferences
    ad_preferences = ad_manager.get_user_ad_preference_data(current_user.id)
    
    return render_template('user_preferences.html', 
                          current_user=current_user,
                          ad_preferences=ad_preferences)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
