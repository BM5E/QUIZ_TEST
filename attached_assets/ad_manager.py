"""
Ad Management Module for BookQuiz

This module handles ad settings, user preferences for ads, and integration 
with various ad networks for monetization.
"""

import os
import json
from flask import session, current_app
from flask_login import current_user

# Default ad configuration
DEFAULT_AD_CONFIG = {
    'enabled': True,                   # Master switch for ads in the application
    'test_mode': True,                 # Show placeholder ads during development
    'refreshInterval': 45,             # Seconds between ad refreshes
    'maxAdsPerPage': 3,                # Maximum number of ads to show per page
    'userOptOut': False,               # Whether the current user has opted out of ads
    'placements': {                    # Enabled ad placements throughout the app
        'homepage': True,              # Ad at bottom of homepage
        'quizSidebar': True,           # Side ads during quiz taking
        'quizResults': True,           # Ad in quiz results before buttons
        'profile': False               # Ad in profile page (disabled by default)
    },
    'adNetwork': 'placeholder',        # Current ad network being used
                                       # Options: 'placeholder', 'adsense', 'admanager'
    'adNetworkConfig': {}              # Configuration specific to the ad network
}

def get_ad_config():
    """
    Get the current ad configuration, combining the default config with any
    user-specific settings.
    
    Returns:
        dict: Ad configuration dictionary
    """
    # Start with the default configuration
    config = DEFAULT_AD_CONFIG.copy()
    
    # Apply user-specific ad preferences if user is logged in
    if current_user.is_authenticated:
        # Check if user has opted out of ads
        config['userOptOut'] = has_user_opted_out(current_user.id)
    
    # Handle server-side disabling of ads in development
    if os.environ.get('FLASK_ENV') == 'development':
        config['test_mode'] = True
    
    return config

def has_user_opted_out(user_id):
    """
    Check if a user has opted out of seeing ads.
    
    Args:
        user_id: The user's ID
        
    Returns:
        bool: True if user has opted out, False otherwise
    """
    from models import User
    user = User.query.get(user_id)
    
    # In the future, this will be stored in a user_preferences table
    # For now, returning a placeholder value
    return False

def toggle_user_ad_preference(user_id, enabled=True):
    """
    Toggle or set a user's ad preference.
    
    Args:
        user_id: The user's ID
        enabled: Whether ads should be enabled for this user
        
    Returns:
        bool: True if successful, False otherwise
    """
    # In the future, this will update the user_preferences table
    # For now, returning a placeholder success value
    return True

def get_ad_code_for_placement(placement_id, format='responsive'):
    """
    Generate the appropriate ad code for a given placement.
    
    Args:
        placement_id: The ID of the ad placement
        format: The ad format ('responsive', 'sidebar', etc.)
        
    Returns:
        dict: Ad configuration for the given placement
    """
    config = get_ad_config()
    
    # If user has opted out or ads are disabled, return empty config
    if config['userOptOut'] or not config['enabled']:
        return {'enabled': False}
    
    # Check if this specific placement is enabled
    placement_enabled = config['placements'].get(placement_id, False)
    if not placement_enabled:
        return {'enabled': False}
    
    # Determine appropriate ad size based on placement and format
    size = get_ad_size_for_placement(placement_id, format)
    
    return {
        'enabled': True,
        'network': config['adNetwork'],
        'test_mode': config['test_mode'],
        'placement_id': placement_id,
        'size': size,
        'refreshInterval': config['refreshInterval']
    }

def get_ad_size_for_placement(placement_id, format='responsive'):
    """
    Get the appropriate ad size for a given placement and format.
    
    Args:
        placement_id: The ID of the ad placement
        format: The ad format ('responsive', 'sidebar', etc.)
        
    Returns:
        dict: Width and height dimensions
    """
    # Define standard ad sizes
    sizes = {
        'homepage': {'width': '728', 'height': '90'},
        'quizSidebar': {'width': '300', 'height': '600'},
        'quizResults': {'width': '728', 'height': '90'},
        'profile': {'width': '300', 'height': '250'}
    }
    
    return sizes.get(placement_id, {'width': '300', 'height': '250'})

def get_user_ad_preference_data(user_id):
    """
    Get a dictionary of the user's ad preferences for the settings page.
    
    Args:
        user_id: The user's ID
        
    Returns:
        dict: Dictionary of user ad preferences
    """
    return {
        'adsEnabled': not has_user_opted_out(user_id),
        'lastUpdated': None  # Will be a datetime in the future
    }