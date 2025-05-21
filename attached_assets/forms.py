from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, RadioField, SelectField, IntegerField
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
