from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, SecurityQuestion
from forms import RegistrationForm, LoginForm, SecurityQuestionForm, ResetPasswordForm
from db import db
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Blueprint
auth = Blueprint('auth', __name__)

# Registration route
@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with security questions"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Hash password for security
        hashed_password = generate_password_hash(form.password.data)
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password
        )
        
        try:
            # Add user to database
            db.session.add(user)
            db.session.commit()

            # Store user ID in session for security questions
            session['user_id_for_security'] = user.id
            
            # Redirect to security questions page
            flash('Account created! Please set up your security questions.', 'success')
            return redirect(url_for('auth.setup_security_questions'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('register.html', form=form)

# Security questions setup route
@auth.route('/security-questions', methods=['GET', 'POST'])
def setup_security_questions():
    """Set up security questions for password recovery"""
    # Check if user_id is in session
    user_id = session.get('user_id_for_security')
    if not user_id:
        flash('Please register first.', 'warning')
        return redirect(url_for('auth.register'))
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.register'))
    
    form = SecurityQuestionForm()
    
    if form.validate_on_submit():
        try:
            # Create security question entries
            security_questions = [
                SecurityQuestion(
                    user_id=user.id,
                    question=form.question1.data,
                    answer=generate_password_hash(form.answer1.data.lower())
                ),
                SecurityQuestion(
                    user_id=user.id,
                    question=form.question2.data,
                    answer=generate_password_hash(form.answer2.data.lower())
                ),
                SecurityQuestion(
                    user_id=user.id,
                    question=form.question3.data,
                    answer=generate_password_hash(form.answer3.data.lower())
                )
            ]
            
            # Add security questions to database
            db.session.add_all(security_questions)
            db.session.commit()
            
            # Remove user_id from session
            session.pop('user_id_for_security', None)
            
            # Log in user automatically
            login_user(user)
            
            flash('Security questions set up successfully!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Security questions setup error: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('security_questions.html', form=form)

# Login route
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        # Check if user exists and password is correct
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            
            # Redirect to requested page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
    
    return render_template('login.html', form=form)

# Logout route
@auth.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

# Forgot password route
@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Initiate password reset with email"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Store user ID in session for security verification
            session['reset_user_id'] = user.id
            return redirect(url_for('auth.verify_security_questions'))
        else:
            flash('Email not found.', 'danger')
    
    return render_template('forgot_password.html')

# Verify security questions route
@auth.route('/verify-security', methods=['GET', 'POST'])
def verify_security_questions():
    """Verify security questions for password reset"""
    # Check if reset_user_id is in session
    user_id = session.get('reset_user_id')
    if not user_id:
        flash('Please start the password reset process again.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    # Get security questions for user
    security_questions = SecurityQuestion.query.filter_by(user_id=user.id).all()
    
    if len(security_questions) < 3:
        flash('No security questions found. Please contact support.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        correct_answers = 0
        
        # Check each answer
        for i, question in enumerate(security_questions):
            answer = request.form.get(f'answer{i+1}', '').lower()
            if check_password_hash(question.answer, answer):
                correct_answers += 1
        
        # If all answers are correct, allow password reset
        if correct_answers == len(security_questions):
            session['security_verified'] = True
            return redirect(url_for('auth.reset_password'))
        else:
            flash('One or more security answers are incorrect.', 'danger')
    
    return render_template('verify_security.html', security_questions=security_questions)

# Reset password route
@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password after security verification"""
    # Check if security has been verified
    if not session.get('security_verified'):
        flash('Please verify your security questions first.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    # Check if reset_user_id is in session
    user_id = session.get('reset_user_id')
    if not user_id:
        flash('Please start the password reset process again.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        try:
            # Update password
            user.password_hash = generate_password_hash(form.password.data)
            db.session.commit()
            
            # Clear session variables
            session.pop('reset_user_id', None)
            session.pop('security_verified', None)
            
            flash('Password has been reset successfully! Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Password reset error: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('reset_password.html', form=form)
