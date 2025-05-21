from datetime import datetime
from flask_login import UserMixin
from db import db

class APIKey(db.Model):
    """API keys for various AI services"""
    id = db.Column(db.Integer, primary_key=True)
    api_name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.Integer, default=1)  # Lower number = higher priority
    
    def __repr__(self):
        return f'<APIKey {self.api_name}>'

class Book(db.Model):
    """Books with details from Google Books API"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    author = db.Column(db.String(256), nullable=False)
    isbn = db.Column(db.String(20), nullable=True, unique=True)
    google_books_id = db.Column(db.String(50), nullable=True, unique=True)
    description = db.Column(db.Text, nullable=True)
    publication_year = db.Column(db.Integer, nullable=True)
    genre = db.Column(db.String(100), nullable=True)
    cover_image_url = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('StoredQuestion', backref='book', lazy=True)
    
    def __repr__(self):
        return f'<Book {self.title} by {self.author}>'

class StoredQuestion(db.Model):
    """Pre-generated questions for books"""
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # 'choice' or 'blank'
    difficulty = db.Column(db.String(20), nullable=False)  # 'easy', 'middle', 'hard'
    correct_answer = db.Column(db.String(256), nullable=False)
    option_a = db.Column(db.String(256), nullable=True)
    option_b = db.Column(db.String(256), nullable=True)
    option_c = db.Column(db.String(256), nullable=True)
    option_d = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<StoredQuestion {self.id} for Book {self.book_id}>'

class User(UserMixin, db.Model):
    """User accounts"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    points = db.Column(db.Integer, default=0)
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='user', lazy=True)
    security_questions = db.relationship('SecurityQuestion', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class SecurityQuestion(db.Model):
    """Security questions for password recovery"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(256), nullable=False)  # Store hashed answers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SecurityQuestion {self.id}>'

class Quiz(db.Model):
    """User quiz sessions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    topic_type = db.Column(db.String(50), nullable=False)  # book or author
    challenge_level = db.Column(db.String(50), default='middle')
    question_type = db.Column(db.String(50), default='choice')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    total_questions = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    score = db.Column(db.Float, default=0.0)
    
    # Relationships
    questions = db.relationship('QuizQuestion', backref='quiz', lazy=True, cascade="all, delete-orphan")
    user_answers = db.relationship('UserAnswer', backref='quiz', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Quiz {self.title}>'

class QuizQuestion(db.Model):
    """Individual questions in a quiz"""
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='choice')  # choice or blank
    correct_answer = db.Column(db.String(200), nullable=False)
    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))
    
    # Relationships
    user_answers = db.relationship('UserAnswer', backref='question', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<QuizQuestion {self.id}>'

class UserAnswer(db.Model):
    """User's answers to quiz questions"""
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    user_answer = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<UserAnswer {self.id}>'
