from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, RadioField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class SecurityQuestionForm(FlaskForm):
    # Predefined security questions
    SECURITY_QUESTIONS = [
        ('What was the name of your first pet?', 'What was the name of your first pet?'),
        ('What is your mother\'s maiden name?', 'What is your mother\'s maiden name?'),
        ('What was the name of your primary school?', 'What was the name of your primary school?'),
        ('What is your favorite book?', 'What is your favorite book?'),
        ('In what city were you born?', 'In what city were you born?'),
        ('What was your childhood nickname?', 'What was your childhood nickname?'),
        ('What is the name of your favorite childhood friend?', 'What is the name of your favorite childhood friend?'),
        ('What street did you grow up on?', 'What street did you grow up on?'),
        ('What was the make of your first car?', 'What was the make of your first car?'),
        ('Who is your favorite author?', 'Who is your favorite author?')
    ]
    
    question1 = SelectField('Security Question 1', choices=SECURITY_QUESTIONS, validators=[DataRequired()])
    answer1 = StringField('Answer 1', validators=[DataRequired(), Length(min=2, max=100)])
    
    question2 = SelectField('Security Question 2', choices=SECURITY_QUESTIONS, validators=[DataRequired()])
    answer2 = StringField('Answer 2', validators=[DataRequired(), Length(min=2, max=100)])
    
    question3 = SelectField('Security Question 3', choices=SECURITY_QUESTIONS, validators=[DataRequired()])
    answer3 = StringField('Answer 3', validators=[DataRequired(), Length(min=2, max=100)])
    
    submit = SubmitField('Set Security Questions')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    search_type = RadioField('Search Type', choices=[('book', 'Book'), ('author', 'Author')], default='book')
    submit = SubmitField('Search')

class QuizForm(FlaskForm):
    num_questions = SelectField('Number of Questions', 
                               choices=[(3, '3'), (5, '5'), (10, '10'), (15, '15'), (20, '20'), (30, '30'), (50, '50')], 
                               default=5, coerce=int)
    challenge_level = SelectField('Difficulty Level', 
                                choices=[('easy', 'Easy'), ('middle', 'Medium'), ('hard', 'Hard')],
                                default='middle')
    question_type = SelectField('Question Type', 
                              choices=[('choice', 'Multiple Choice'), ('blank', 'Fill in the Blank'), ('mixed', 'Mixed')],
                              default='choice')
    submit = SubmitField('Start Quiz')
