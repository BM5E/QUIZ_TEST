from datetime import datetime
from flask_login import UserMixin
from db import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_picture = db.Column(db.String(200), default='default.jpg')
    points = db.Column(db.Integer, default=0)
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='user', lazy=True)
    achievements = db.relationship('Achievement', backref='user', lazy=True)
    shared_items = db.relationship('SharedContent', backref='creator', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Quiz(db.Model):
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
    attempt_number = db.Column(db.Integer, default=1)
    
    # Relationships
    questions = db.relationship('QuizQuestion', backref='quiz', lazy=True, cascade="all, delete-orphan")
    user_answers = db.relationship('UserAnswer', backref='quiz', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Quiz {self.title}>'

class QuizQuestion(db.Model):
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
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    user_answer = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<UserAnswer {self.id}>'

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    badge_icon = db.Column(db.String(200))  # Font-awesome or Feather icon name
    achieved_at = db.Column(db.DateTime, default=datetime.utcnow)
    achievement_type = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=10)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'

class SharedContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    share_key = db.Column(db.String(64), unique=True, nullable=False)
    content_type = db.Column(db.String(50), nullable=False)  # 'quiz' or 'achievement'
    content_id = db.Column(db.Integer, nullable=False)  # References either quiz.id or achievement.id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiration date
    is_public = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    
    # Relationship updated to avoid conflicts with 'creator' backref
    user = db.relationship('User', backref=db.backref('shared_content', lazy=True, overlaps="creator,shared_items"))
    
    def __repr__(self):
        return f'<SharedContent {self.content_type}:{self.content_id}>'
