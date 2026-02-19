"""Token storage and persistence utilities for OAuth authentication."""

import json
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Token storage directory
TOKEN_STORAGE_DIR = ".auth_tokens"


def ensure_storage_dir():
    """Ensure token storage directory exists."""
    if not os.path.exists(TOKEN_STORAGE_DIR):
        os.makedirs(TOKEN_STORAGE_DIR, exist_ok=True)


def save_token(provider: str, user_email: str, token_data: Dict) -> bool:
    """
    Save OAuth token to persistent storage.
    
    Args:
        provider: OAuth provider ('jira' or 'microsoft')
        user_email: User email address
        token_data: Token data dictionary with access_token, refresh_token, etc.
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        ensure_storage_dir()
        
        # Create a safe filename from email
        safe_email = user_email.replace('@', '_at_').replace('.', '_')
        filename = f"{provider}_{safe_email}.json"
        filepath = os.path.join(TOKEN_STORAGE_DIR, filename)
        
        # Add timestamp and provider info
        token_record = {
            'provider': provider,
            'user_email': user_email,
            'token_data': token_data,
            'saved_at': __import__('time').time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(token_record, f)
        
        logger.info(f"Token saved for {provider} user {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save token: {str(e)}")
        return False


def load_token(provider: str, user_email: str) -> Optional[Dict]:
    """
    Load OAuth token from persistent storage.
    
    Args:
        provider: OAuth provider ('jira' or 'microsoft')
        user_email: User email address
        
    Returns:
        Token data dictionary if found, None otherwise
    """
    try:
        ensure_storage_dir()
        
        safe_email = user_email.replace('@', '_at_').replace('.', '_')
        filename = f"{provider}_{safe_email}.json"
        filepath = os.path.join(TOKEN_STORAGE_DIR, filename)
        
        if not os.path.exists(filepath):
            logger.info(f"No token found for {provider} user {user_email}")
            return None
        
        with open(filepath, 'r') as f:
            token_record = json.load(f)
        
        token_data = token_record.get('token_data')
        logger.info(f"Token loaded for {provider} user {user_email}")
        return token_data
        
    except Exception as e:
        logger.error(f"Failed to load token: {str(e)}")
        return None


def is_token_valid(token_data: Optional[Dict]) -> bool:
    """
    Check if token data exists and is valid.
    
    Args:
        token_data: Token data dictionary
        
    Returns:
        True if token is valid, False otherwise
    """
    if not token_data:
        return False
    
    # Check if it has the essential access token
    if 'access_token' not in token_data:
        return False
    
    # Check if token has expired (optional expiry field)
    if 'expires_at' in token_data:
        import time
        if time.time() > token_data['expires_at']:
            return False
    
    return True


def get_user_email_from_token(token_data: Optional[Dict]) -> Optional[str]:
    """
    Extract user email from token data.
    
    Args:
        token_data: Token data dictionary that may contain email info
        
    Returns:
        User email if found, None otherwise
    """
    if not token_data:
        return None
    
    # Try common email field names in token responses
    email_fields = ['email', 'mail', 'userPrincipalName', 'preferred_username']
    
    for field in email_fields:
        if field in token_data:
            return token_data[field]
    
    return None


def delete_token(provider: str, user_email: str) -> bool:
    """
    Delete saved token for a user.
    
    Args:
        provider: OAuth provider ('jira' or 'microsoft')
        user_email: User email address
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        safe_email = user_email.replace('@', '_at_').replace('.', '_')
        filename = f"{provider}_{safe_email}.json"
        filepath = os.path.join(TOKEN_STORAGE_DIR, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Token deleted for {provider} user {user_email}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to delete token: {str(e)}")
        return False


def list_saved_tokens() -> list:
    """
    List all saved tokens.
    
    Returns:
        List of tuples (provider, user_email)
    """
    try:
        tokens = []
        ensure_storage_dir()
        
        for filename in os.listdir(TOKEN_STORAGE_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(TOKEN_STORAGE_DIR, filename)
                try:
                    with open(filepath, 'r') as f:
                        token_record = json.load(f)
                        tokens.append((
                            token_record.get('provider'),
                            token_record.get('user_email')
                        ))
                except Exception as e:
                    logger.warning(f"Failed to read token file {filename}: {str(e)}")
        
        return tokens
        
    except Exception as e:
        logger.error(f"Failed to list tokens: {str(e)}")
        return []


def clear_all_tokens() -> bool:
    """
    Clear all saved tokens.
    
    Returns:
        True if cleared successfully, False otherwise
    """
    try:
        if os.path.exists(TOKEN_STORAGE_DIR):
            import shutil
            shutil.rmtree(TOKEN_STORAGE_DIR)
            logger.info("All tokens cleared")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to clear tokens: {str(e)}")
        return False
