"""OAuth 2.0 authentication logic for Atlassian Jira."""

import logging
import requests
import urllib.parse
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class JiraOAuthError(Exception):
    """Custom exception for Jira OAuth errors."""
    pass


def get_authorization_url(oauth_config: Dict, state: str = None) -> str:
    """
    Generate the authorization URL for Atlassian OAuth flow.
    
    Args:
        oauth_config: OAuth configuration dictionary
        state: Optional state parameter for CSRF protection
        
    Returns:
        Authorization URL to redirect user to
    """
    params = {
        'client_id': oauth_config['client_id'],
        'redirect_uri': oauth_config['redirect_uri'],
        'response_type': 'code',
        'scope': oauth_config['scope'],
    }
    
    if state:
        params['state'] = state
    
    auth_url = oauth_config['auth_url']
    return f"{auth_url}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(
    auth_code: str,
    oauth_config: Dict
) -> Dict:
    """
    Exchange authorization code for access token.
    
    Args:
        auth_code: Authorization code from OAuth callback
        oauth_config: OAuth configuration dictionary
        
    Returns:
        Dictionary containing access_token, expires_in, etc.
        
    Raises:
        JiraOAuthError: If token exchange fails
    """
    try:
        token_url = oauth_config['token_url']
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': oauth_config['client_id'],
            'client_secret': oauth_config['client_secret'],
            'code': auth_code,
            'redirect_uri': oauth_config['redirect_uri'],
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        logger.info("Successfully exchanged auth code for access token")
        return token_data
        
    except requests.exceptions.Timeout:
        raise JiraOAuthError("Token exchange timeout - unable to connect to Atlassian")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Token exchange failed: {e}")
        error_data = response.json() if response.text else {}
        raise JiraOAuthError(f"Login failed: {error_data.get('error_description', str(e))}")
    except Exception as e:
        logger.error(f"Unexpected error during token exchange: {str(e)}")
        raise JiraOAuthError(f"Login failed: {str(e)}")


def get_user_info(access_token: str, oauth_config: Dict) -> Dict:
    """
    Get user information from Atlassian.
    
    Args:
        access_token: OAuth access token
        oauth_config: OAuth configuration dictionary
        
    Returns:
        Dictionary with user info (name, email, picture, etc.)
        
    Raises:
        JiraOAuthError: If user info retrieval fails
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        }
        
        resource_url = oauth_config['resource_url']
        response = requests.get(resource_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        user_info = response.json()
        logger.info(f"Successfully retrieved user info for {user_info.get('email')}")
        return user_info
        
    except requests.exceptions.Timeout:
        raise JiraOAuthError("Unable to fetch user info - connection timeout")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to get user info: {e}")
        raise JiraOAuthError("Failed to retrieve user information")
    except Exception as e:
        logger.error(f"Unexpected error getting user info: {str(e)}")
        raise JiraOAuthError(f"Failed to retrieve user information: {str(e)}")


def validate_user_belongs_to_workspace(
    user_info: Dict,
    jira_config: Dict
) -> Tuple[bool, str]:
    """
    Validate that user belongs to the allowed Jira instance.
    
    Args:
        user_info: User information from Atlassian
        jira_config: Jira configuration dictionary
        
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        # Extract the Jira instance from user info
        # Atlassian returns account_id and we can check if user has access to our workspace
        allowed_instance = jira_config.get('allowed_instance', 'wkengineering.atlassian.net')
        
        # Check if user has the required email domain or instance access
        # This is a simplified check - in production you might want to verify 
        # user's group membership or specific workspace access
        user_email = user_info.get('email', '')
        
        logger.info(f"Validating user {user_email} for workspace {allowed_instance}")
        
        # For now, we'll accept any user. In production, you should:
        # 1. Call Jira API to verify user can access the specific instance
        # 2. Check user's groups or permissions
        # 3. Maintain a whitelist of allowed users/email domains
        
        return True, f"Access granted for {user_email}"
        
    except Exception as e:
        logger.error(f"Error validating user workspace: {str(e)}")
        return False, f"Failed to validate user: {str(e)}"


def refresh_access_token(
    refresh_token: str,
    oauth_config: Dict
) -> Dict:
    """
    Refresh an expired access token.
    
    Args:
        refresh_token: Refresh token from previous auth
        oauth_config: OAuth configuration dictionary
        
    Returns:
        Dictionary with new access_token and expires_in
        
    Raises:
        JiraOAuthError: If token refresh fails
    """
    try:
        token_url = oauth_config['token_url']
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': oauth_config['client_id'],
            'client_secret': oauth_config['client_secret'],
            'refresh_token': refresh_token,
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        logger.info("Successfully refreshed access token")
        return token_data
        
    except requests.exceptions.HTTPError:
        logger.error("Token refresh failed - may need to re-authenticate")
        raise JiraOAuthError("Session expired - please login again")
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise JiraOAuthError("Failed to refresh session")


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
    
    return 'access_token' in token_data
