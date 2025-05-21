from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Quiz, QuizQuestion, UserAnswer, Achievement
from forms import QuizForm
from db import db
from openai_service import generate_quiz_questions
from social_utils import create_shared_content, get_absolute_share_url, get_social_share_links
from utils import get_quiz_emoji, format_challenge_level, get_topic_display
from datetime import datetime
import random
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Blueprint
quiz = Blueprint('quiz', __name__)

# Create quiz route
@quiz.route('/create', methods=['GET', 'POST'])
@login_required
def create_quiz():
    """Create a new quiz"""
    from book_service import get_book_details, save_book_to_database, check_book_exists
    from ai_quiz_service import get_stored_questions_for_quiz
    
    form = QuizForm()
    
    if form.validate_on_submit():
        # Get form data
        topic = request.form.get('topic')
        topic_type = request.form.get('topic_type')
        num_questions = form.num_questions.data
        challenge_level = form.challenge_level.data
        question_type = form.question_type.data
        google_books_id = request.form.get('google_books_id')
        
        if not topic or not topic_type:
            flash('Please provide a topic and select a topic type.', 'danger')
            return render_template('create_quiz.html', form=form)
        
        try:
            # If we have a Google Books ID, get book details and save to database
            book = None
            if google_books_id and topic_type == 'book':
                # Get detailed book information
                book_details = get_book_details(google_books_id)
                if book_details:
                    # Save or get existing book in database
                    book = save_book_to_database(book_details)
            
            # If book is already in our database, check for existing questions
            stored_questions = []
            if book:
                stored_questions = get_stored_questions_for_quiz(
                    book.id,
                    num_questions=num_questions,
                    difficulty=challenge_level,
                    question_type=question_type
                )
            
            # Create new quiz
            new_quiz = Quiz()
            new_quiz.user_id = current_user.id
            new_quiz.title = f"Quiz on {topic}"
            new_quiz.topic = topic
            new_quiz.topic_type = topic_type
            new_quiz.challenge_level = challenge_level
            new_quiz.question_type = question_type
            new_quiz.total_questions = num_questions
            
            db.session.add(new_quiz)
            db.session.commit()
            
            # Use stored questions if available, otherwise generate new ones
            if stored_questions:
                questions = stored_questions
                logger.info(f"Using {len(questions)} stored questions for quiz")
            else:
                # Generate fresh questions using AI service
                questions = generate_quiz_questions(
                    topic, 
                    topic_type, 
                    num_questions, 
                    challenge_level, 
                    question_type
                )
            
            # Create quiz questions in database
            for q in questions:
                question = QuizQuestion()
                question.quiz_id = new_quiz.id
                
                # Handle different field names between stored questions and generated questions
                if 'question' in q:
                    question.question_text = q.get('question')
                elif 'question_text' in q:
                    question.question_text = q.get('question_text')
                
                question.question_type = q.get('question_type', 'choice')
                question.correct_answer = q.get('correct_answer', '')
                
                # Add options for multiple choice questions
                if q.get('question_type') == 'choice':
                    if 'options' in q:
                        question.option_a = q['options'][0]
                        question.option_b = q['options'][1]
                        question.option_c = q['options'][2]
                        question.option_d = q['options'][3]
                    else:
                        # Handle if options are stored individually
                        question.option_a = q.get('option_a', '')
                        question.option_b = q.get('option_b', '')
                        question.option_c = q.get('option_c', '')
                        question.option_d = q.get('option_d', '')
                
                db.session.add(question)
            
            db.session.commit()
            
            # Redirect to the quiz
            return redirect(url_for('quiz.take_quiz', quiz_id=new_quiz.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Quiz creation error: {str(e)}")
            flash('An error occurred while creating the quiz. Please try again.', 'danger')
    
    return render_template('create_quiz.html', form=form)

# Take quiz route
@quiz.route('/take/<int:quiz_id>')
@login_required
def take_quiz(quiz_id):
    """Take a quiz"""
    # Get quiz
    quiz_data = Quiz.query.get_or_404(quiz_id)
    
    # Check if user is authorized to take this quiz
    if quiz_data.user_id != current_user.id:
        flash('You are not authorized to view this quiz.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Check if quiz is already completed
    if quiz_data.is_completed:
        flash('This quiz has already been completed.', 'info')
        return redirect(url_for('quiz.quiz_results', quiz_id=quiz_id))
    
    # Get quiz questions
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
    
    # Check if questions exist
    if not questions:
        flash('No questions found for this quiz.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template(
        'quiz.html',
        quiz=quiz_data,
        questions=questions,
        topic_display=get_topic_display(quiz_data.topic, quiz_data.topic_type),
        challenge_level=format_challenge_level(quiz_data.challenge_level)
    )

# Submit quiz route
@quiz.route('/submit/<int:quiz_id>', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    """Submit quiz answers"""
    # Get quiz
    quiz_data = Quiz.query.get_or_404(quiz_id)
    
    # Check if user is authorized to submit this quiz
    if quiz_data.user_id != current_user.id:
        flash('You are not authorized to submit this quiz.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Check if quiz is already completed
    if quiz_data.is_completed:
        flash('This quiz has already been completed.', 'warning')
        return redirect(url_for('quiz.quiz_results', quiz_id=quiz_id))
    
    try:
        # Get quiz questions
        questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
        
        # Process user answers
        correct_answers = 0
        
        for question in questions:
            # Get user's answer
            user_answer = request.form.get(f'question_{question.id}', '')
            
            # Check if answer is correct
            is_correct = False
            if question.question_type == 'choice':
                is_correct = user_answer == question.correct_answer
            else:  # blank
                # Case-insensitive comparison for fill-in-the-blank
                is_correct = user_answer.lower() == question.correct_answer.lower()
            
            if is_correct:
                correct_answers += 1
            
            # Save user's answer
            answer = UserAnswer()
            answer.quiz_id = quiz_id
            answer.question_id = question.id
            answer.user_answer = user_answer
            answer.is_correct = is_correct
            
            db.session.add(answer)
        
        # Update quiz with results
        score = 0
        if len(questions) > 0:
            score = (correct_answers / len(questions)) * 100
            
        quiz_data.is_completed = True
        quiz_data.completed_at = datetime.utcnow()
        quiz_data.correct_answers = correct_answers
        quiz_data.score = score
        
        # Update user points
        points_earned = int(score / 10)  # 10% of score as points
        current_user.points += points_earned
        
        db.session.commit()
        
        # Check for achievements
        check_for_achievements(quiz_data)
        
        return redirect(url_for('quiz.quiz_results', quiz_id=quiz_id))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Quiz submission error: {str(e)}")
        flash('An error occurred while submitting the quiz. Please try again.', 'danger')
        return redirect(url_for('quiz.take_quiz', quiz_id=quiz_id))

# Quiz results route
@quiz.route('/results/<int:quiz_id>')
@login_required
def quiz_results(quiz_id):
    """View quiz results"""
    # Get quiz
    quiz_data = Quiz.query.get_or_404(quiz_id)
    
    # Check if user is authorized to view this quiz
    if quiz_data.user_id != current_user.id:
        flash('You are not authorized to view these results.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Check if quiz is completed
    if not quiz_data.is_completed:
        flash('This quiz has not been completed yet.', 'warning')
        return redirect(url_for('quiz.take_quiz', quiz_id=quiz_id))
    
    # Get questions and answers
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
    user_answers = UserAnswer.query.filter_by(quiz_id=quiz_id).all()
    
    # Organize user answers by question ID for easy access
    answers_by_question = {answer.question_id: answer for answer in user_answers}
    
    # Generate share URL
    shared_content = create_shared_content(current_user.id, 'quiz', quiz_id)
    share_url = get_absolute_share_url(shared_content.share_key)
    
    # Generate social sharing links
    share_title = f"I scored {int(quiz_data.score)}% on a quiz about {quiz_data.topic}!"
    share_description = f"Check out my quiz results on BookQuiz!"
    social_links = get_social_share_links(share_url, share_title, share_description)
    
    return render_template(
        'quiz_results.html',
        quiz=quiz_data,
        questions=questions,
        answers=answers_by_question,
        emoji=get_quiz_emoji(quiz_data.score),
        topic_display=get_topic_display(quiz_data.topic, quiz_data.topic_type),
        challenge_level=format_challenge_level(quiz_data.challenge_level),
        share_url=share_url,
        social_links=social_links
    )

# Helper function to check for achievements
def check_for_achievements(quiz):
    """Check if user has earned any achievements based on quiz results"""
    user = User.query.get(quiz.user_id)
    
    # Count user's completed quizzes
    completed_quizzes_count = Quiz.query.filter_by(user_id=user.id, is_completed=True).count()
    
    # Get user's high score
    high_score_quiz = Quiz.query.filter_by(user_id=user.id, is_completed=True).order_by(Quiz.score.desc()).first()
    
    # Achievement: First quiz completed
    if completed_quizzes_count == 1:
        create_achievement(
            user.id,
            "First Quiz",
            "Completed your first quiz!",
            "award",
            "quiz_completion",
            10
        )
    
    # Achievement: 5 quizzes completed
    if completed_quizzes_count == 5:
        create_achievement(
            user.id,
            "Quiz Enthusiast",
            "Completed 5 quizzes!",
            "award-fill",
            "quiz_completion",
            25
        )
    
    # Achievement: Perfect score
    if quiz.score == 100:
        create_achievement(
            user.id,
            "Perfect Score",
            f"Achieved a perfect score on a quiz about {quiz.topic}!",
            "star-fill",
            "quiz_score",
            50
        )
    
    # Achievement: High score (90%+)
    if quiz.score >= 90 and high_score_quiz and high_score_quiz.id == quiz.id:
        create_achievement(
            user.id,
            "High Scorer",
            f"Achieved a score of {int(quiz.score)}% on a quiz about {quiz.topic}!",
            "trophy",
            "quiz_score",
            30
        )
    
    # Achievement: Hard quiz mastery
    if quiz.challenge_level == 'hard' and quiz.score >= 80:
        create_achievement(
            user.id,
            "Hard Quiz Master",
            f"Scored over 80% on a hard quiz about {quiz.topic}!",
            "award-fill",
            "difficulty",
            40
        )

# Helper function to create achievements
def create_achievement(user_id, name, description, badge_icon, achievement_type, points):
    """Create a new achievement for a user"""
    # Check if user already has this achievement
    existing = Achievement.query.filter_by(user_id=user_id, name=name).first()
    if existing:
        return
    
    # Create new achievement
    achievement = Achievement()
    achievement.user_id = user_id
    achievement.name = name
    achievement.description = description
    achievement.badge_icon = badge_icon
    achievement.achievement_type = achievement_type
    achievement.points = points
    
    try:
        # Add achievement to database
        db.session.add(achievement)
        db.session.commit()
        
        # Update user points
        user = User.query.get(user_id)
        user.points += points
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Achievement creation error: {str(e)}")

# Import User model (needed for achievements)
from models import User
