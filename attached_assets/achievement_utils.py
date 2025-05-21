from datetime import datetime
from models import Achievement

# Define achievement types and criteria
ACHIEVEMENTS = {
    'first_quiz': {
        'name': 'First Quiz',
        'description': 'Completed your first book quiz!',
        'badge_icon': 'award',
        'points': 10
    },
    'perfect_score': {
        'name': 'Perfect Score',
        'description': 'Got a perfect 100% on a quiz!',
        'badge_icon': 'star',
        'points': 50
    },
    'quiz_streak': {
        'name': 'Quiz Streak',
        'description': 'Completed 5 quizzes in a row!',
        'badge_icon': 'zap',
        'points': 30
    },
    'bookworm': {
        'name': 'Bookworm',
        'description': 'Completed quizzes on 10 different books!',
        'badge_icon': 'book',
        'points': 40
    },
    'author_expert': {
        'name': 'Author Expert',
        'description': 'Completed quizzes on 5 different authors!',
        'badge_icon': 'feather',
        'points': 40
    },
    'high_scorer': {
        'name': 'High Scorer',
        'description': 'Scored 80% or higher on 3 different quizzes!',
        'badge_icon': 'trending-up',
        'points': 30
    },
    'genre_explorer': {
        'name': 'Genre Explorer',
        'description': 'Completed quizzes on books from 3 different genres!',
        'badge_icon': 'compass',
        'points': 35
    },
    'quiz_master': {
        'name': 'Quiz Master',
        'description': 'Completed 20 quizzes in total!',
        'badge_icon': 'award',
        'points': 100
    }
}

def check_achievements(user_id, quiz, session):
    """
    Check if user has earned any achievements after completing a quiz
    
    Args:
        user_id: The user's ID
        quiz: The completed quiz
        session: Database session
    """
    # Import here to avoid circular imports
    from models import Quiz, User, Achievement
    
    achievements_earned = []
    
    # Get user and all their completed quizzes
    user = User.query.get(user_id)
    completed_quizzes = Quiz.query.filter_by(user_id=user_id, is_completed=True).all()
    
    # Check for first quiz achievement
    if len(completed_quizzes) == 1:
        achievements_earned.append('first_quiz')
    
    # Check for perfect score achievement
    if quiz.score == 100:
        achievements_earned.append('perfect_score')
    
    # Check for quiz streak (5 in a row)
    if len(completed_quizzes) >= 5:
        # Sort by completion date
        recent_quizzes = sorted(completed_quizzes, key=lambda q: q.completed_at, reverse=True)[:5]
        if all(q.score > 0 for q in recent_quizzes):  # All must be completed
            # Check if user already has this achievement
            if not Achievement.query.filter_by(user_id=user_id, achievement_type='quiz_streak').first():
                achievements_earned.append('quiz_streak')
    
    # Check for bookworm (10 different books)
    book_quizzes = Quiz.query.filter_by(user_id=user_id, topic_type='book', is_completed=True).all()
    unique_books = set(q.topic for q in book_quizzes)
    if len(unique_books) >= 10:
        # Check if user already has this achievement
        if not Achievement.query.filter_by(user_id=user_id, achievement_type='bookworm').first():
            achievements_earned.append('bookworm')
    
    # Check for author expert (5 different authors)
    author_quizzes = Quiz.query.filter_by(user_id=user_id, topic_type='author', is_completed=True).all()
    unique_authors = set(q.topic for q in author_quizzes)
    if len(unique_authors) >= 5:
        # Check if user already has this achievement
        if not Achievement.query.filter_by(user_id=user_id, achievement_type='author_expert').first():
            achievements_earned.append('author_expert')
    
    # Check for high scorer (80%+ on 3 different quizzes)
    high_score_quizzes = [q for q in completed_quizzes if q.score >= 80]
    if len(high_score_quizzes) >= 3:
        # Check if user already has this achievement
        if not Achievement.query.filter_by(user_id=user_id, achievement_type='high_scorer').first():
            achievements_earned.append('high_scorer')
    
    # Check for quiz master (20 total quizzes)
    if len(completed_quizzes) >= 20:
        # Check if user already has this achievement
        if not Achievement.query.filter_by(user_id=user_id, achievement_type='quiz_master').first():
            achievements_earned.append('quiz_master')
    
    # Award the achievements
    points_earned = 0
    for achievement_type in achievements_earned:
        achievement_data = ACHIEVEMENTS[achievement_type]
        
        # Check if user already has this achievement
        existing = Achievement.query.filter_by(
            user_id=user_id, 
            achievement_type=achievement_type
        ).first()
        
        if not existing:
            # Create new achievement
            new_achievement = Achievement(
                user_id=user_id,
                name=achievement_data['name'],
                description=achievement_data['description'],
                badge_icon=achievement_data['badge_icon'],
                achievement_type=achievement_type,
                points=achievement_data['points'],
                achieved_at=datetime.utcnow()
            )
            session.add(new_achievement)
            
            # Add points to user
            points_earned += achievement_data['points']
    
    # Update user points
    if points_earned > 0:
        user.points += points_earned
        session.commit()

def get_achievement_progress(user_id):
    """
    Get the user's progress toward each achievement
    
    Args:
        user_id: The user's ID
        
    Returns:
        dict: Dictionary with achievement progress
    """
    # Import here to avoid circular imports
    from models import Quiz, Achievement
    
    # Get user's completed quizzes
    completed_quizzes = Quiz.query.filter_by(user_id=user_id, is_completed=True).all()
    
    # Get user's achievements
    user_achievements = Achievement.query.filter_by(user_id=user_id).all()
    
    # Convert to dict for easy lookup
    achievement_dict = {a.achievement_type: a for a in user_achievements}
    
    # Calculate progress for each achievement
    progress = {}
    
    # First quiz
    if 'first_quiz' in achievement_dict:
        progress['first_quiz'] = {'earned': True, 'progress': 1, 'total': 1}
    else:
        progress['first_quiz'] = {'earned': False, 'progress': min(len(completed_quizzes), 1), 'total': 1}
    
    # Perfect score
    perfect_quizzes = [q for q in completed_quizzes if q.score == 100]
    if 'perfect_score' in achievement_dict:
        progress['perfect_score'] = {'earned': True, 'progress': 1, 'total': 1}
    else:
        progress['perfect_score'] = {'earned': False, 'progress': min(len(perfect_quizzes), 1), 'total': 1}
    
    # Quiz streak
    if 'quiz_streak' in achievement_dict:
        progress['quiz_streak'] = {'earned': True, 'progress': 5, 'total': 5}
    else:
        progress['quiz_streak'] = {'earned': False, 'progress': min(len(completed_quizzes), 5), 'total': 5}
    
    # Bookworm
    book_quizzes = [q for q in completed_quizzes if q.topic_type == 'book']
    unique_books = set(q.topic for q in book_quizzes)
    if 'bookworm' in achievement_dict:
        progress['bookworm'] = {'earned': True, 'progress': 10, 'total': 10}
    else:
        progress['bookworm'] = {'earned': False, 'progress': min(len(unique_books), 10), 'total': 10}
    
    # Author expert
    author_quizzes = [q for q in completed_quizzes if q.topic_type == 'author']
    unique_authors = set(q.topic for q in author_quizzes)
    if 'author_expert' in achievement_dict:
        progress['author_expert'] = {'earned': True, 'progress': 5, 'total': 5}
    else:
        progress['author_expert'] = {'earned': False, 'progress': min(len(unique_authors), 5), 'total': 5}
    
    # High scorer
    high_score_quizzes = [q for q in completed_quizzes if q.score >= 80]
    if 'high_scorer' in achievement_dict:
        progress['high_scorer'] = {'earned': True, 'progress': 3, 'total': 3}
    else:
        progress['high_scorer'] = {'earned': False, 'progress': min(len(high_score_quizzes), 3), 'total': 3}
    
    # Quiz master
    if 'quiz_master' in achievement_dict:
        progress['quiz_master'] = {'earned': True, 'progress': 20, 'total': 20}
    else:
        progress['quiz_master'] = {'earned': False, 'progress': min(len(completed_quizzes), 20), 'total': 20}
    
    return progress
