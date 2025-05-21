import logging
import json
from datetime import datetime
from models import APIKey, db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AIServiceManager:
    """Manager for handling multiple AI service providers and their API keys"""
    
    @staticmethod
    def get_api_key(api_name=None):
        """
        Get an active API key for a specific AI service or the highest priority active key
        
        Args:
            api_name (str, optional): Name of the AI service (e.g., 'openai', 'gemini')
            
        Returns:
            tuple: (api_name, api_key) or (None, None) if no active key is found
        """
        try:
            query = APIKey.query.filter_by(is_active=True)
            
            # Filter by specific API if requested
            if api_name:
                key = query.filter_by(api_name=api_name).order_by(APIKey.priority).first()
                if key:
                    # Update last_used timestamp
                    key.last_used = datetime.utcnow()
                    db.session.commit()
                    return key.api_name, key.api_key
                return None, None
            
            # Otherwise, get highest priority active key
            key = query.order_by(APIKey.priority).first()
            if key:
                # Update last_used timestamp
                key.last_used = datetime.utcnow()
                db.session.commit()
                return key.api_name, key.api_key
            
            return None, None
        
        except Exception as e:
            logger.error(f"Error getting API key: {str(e)}")
            return None, None
    
    @staticmethod
    def add_api_key(api_name, api_key, description=None, priority=1):
        """
        Add a new API key to the database
        
        Args:
            api_name (str): Name of the AI service
            api_key (str): API key value
            description (str, optional): Description of the API key
            priority (int, optional): Priority level (lower = higher priority)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if key already exists
            existing_key = APIKey.query.filter_by(api_name=api_name, api_key=api_key).first()
            if existing_key:
                # Update existing key
                existing_key.description = description or existing_key.description
                existing_key.priority = priority
                existing_key.is_active = True
                db.session.commit()
                return True
            
            # Create new API key
            new_key = APIKey()
            new_key.api_name = api_name
            new_key.api_key = api_key
            new_key.description = description
            new_key.priority = priority
            new_key.is_active = True
            
            db.session.add(new_key)
            db.session.commit()
            return True
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding API key: {str(e)}")
            return False
    
    @staticmethod
    def deactivate_api_key(api_name=None, api_key=None):
        """
        Deactivate an API key (for example, when it's rate limited)
        
        Args:
            api_name (str, optional): Name of the AI service
            api_key (str, optional): Specific API key to deactivate
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = APIKey.query
            
            if api_name and api_key:
                key = query.filter_by(api_name=api_name, api_key=api_key).first()
            elif api_name:
                key = query.filter_by(api_name=api_name).first()
            elif api_key:
                key = query.filter_by(api_key=api_key).first()
            else:
                return False
            
            if key:
                key.is_active = False
                db.session.commit()
                return True
            
            return False
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deactivating API key: {str(e)}")
            return False
    
    @staticmethod
    def get_all_api_keys():
        """
        Get all API keys in the database
        
        Returns:
            list: List of API key dictionaries
        """
        try:
            keys = APIKey.query.order_by(APIKey.api_name, APIKey.priority).all()
            
            result = []
            for key in keys:
                # Mask the actual key value for security
                masked_key = key.api_key[:4] + "..." + key.api_key[-4:] if len(key.api_key) > 8 else "***"
                
                result.append({
                    'id': key.id,
                    'api_name': key.api_name,
                    'masked_key': masked_key,
                    'description': key.description,
                    'is_active': key.is_active,
                    'priority': key.priority,
                    'last_used': key.last_used.strftime('%Y-%m-%d %H:%M:%S') if key.last_used else None
                })
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting all API keys: {str(e)}")
            return []