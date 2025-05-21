import os
import secrets
import string
import urllib.parse
from datetime import datetime, timedelta
from flask import url_for
from models import SharedContent, Quiz, Achievement, User
from db import db

def generate_share_key(length=10):
    """
    Generate a random share key for shared content.
    
    Args:
        length (int): Length of the share key
        
    Returns:
        str: Random share key
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_shared_content(user_id, content_type, content_id, expires_days=None):
    """
    Create a new shared content entry.
    
    Args:
        user_id (int): ID of the user sharing the content
        content_type (str): Type of content ('quiz' or 'achievement')
        content_id (int): ID of the content being shared
        expires_days (int, optional): Number of days until the share expires
        
    Returns:
        SharedContent: The created shared content object
    """
    # Check if the content already has a share link
    existing_share = SharedContent.query.filter_by(
        user_id=user_id,
        content_type=content_type,
        content_id=content_id
    ).first()
    
    if existing_share:
        return existing_share
    
    # Generate a unique share key
    while True:
        share_key = generate_share_key()
        if not SharedContent.query.filter_by(share_key=share_key).first():
            break
    
    # Set expiration date if provided
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    # Create shared content entry
    shared_content = SharedContent(
        user_id=user_id,
        share_key=share_key,
        content_type=content_type,
        content_id=content_id,
        expires_at=expires_at,
        is_public=True
    )
    
    db.session.add(shared_content)
    db.session.commit()
    
    return shared_content

def get_absolute_share_url(share_key):
    """
    Get the absolute URL for a shared content item.
    
    Args:
        share_key (str): The share key of the content
        
    Returns:
        str: Absolute URL for accessing the shared content
    """
    base_url = os.environ.get('BASE_URL', 'https://bookquiz.replit.app')
    relative_url = url_for('view_shared', share_key=share_key)
    return urllib.parse.urljoin(base_url, relative_url)

def get_social_share_links(share_url, title, description):
    """
    Generate social media sharing links.
    
    Args:
        share_url (str): URL to share
        title (str): Title of the content
        description (str): Description of the content
        
    Returns:
        dict: Dictionary of social media sharing links
    """
    encoded_url = urllib.parse.quote(share_url)
    encoded_title = urllib.parse.quote(title)
    encoded_description = urllib.parse.quote(description)
    
    return {
        'twitter': f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_title}",
        'facebook': f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
        'linkedin': f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
        'whatsapp': f"https://api.whatsapp.com/send?text={encoded_title}%20{encoded_url}",
        'email': f"mailto:?subject={encoded_title}&body={encoded_description}%0A%0A{encoded_url}"
    }

def get_shared_content(share_key):
    """
    Get shared content and associated data by share key.
    
    Args:
        share_key (str): The share key to look up
        
    Returns:
        tuple: (shared_content, content_object, user) or (None, None, None) if not found
    """
    shared_content = SharedContent.query.filter_by(share_key=share_key).first()
    
    if not shared_content:
        return None, None, None
    
    # Check if expired
    if shared_content.expires_at and shared_content.expires_at < datetime.utcnow():
        return None, None, None
    
    # Increment view count
    shared_content.view_count += 1
    db.session.commit()
    
    # Get the actual content
    if shared_content.content_type == 'quiz':
        content = Quiz.query.get(shared_content.content_id)
    elif shared_content.content_type == 'achievement':
        content = Achievement.query.get(shared_content.content_id)
    else:
        content = None
    
    # Get the user
    user = User.query.get(shared_content.user_id)
    
    return shared_content, content, user