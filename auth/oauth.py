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
    full_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    
    # Debug logging
    logger.info(f"Generated OAuth URL: {full_url}")
    logger.info(f"Redirect URI in request: {oauth_config['redirect_uri']}")
    
    return full_url


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
        logger.info(f"Requesting user info from: {resource_url}")
        
        response = requests.get(resource_url, headers=headers, timeout=10)
        
        # Log response status and content
        logger.info(f"User info response status: {response.status_code}")
        logger.debug(f"User info response: {response.text}")
        
        response.raise_for_status()
        
        user_info = response.json()
        
        # Atlassian /me endpoint returns: account_id, email, name, picture
        logger.info(f"Successfully retrieved user info: {user_info}")
        
        return user_info
        
    except requests.exceptions.Timeout:
        logger.error("User info request timeout")
        raise JiraOAuthError("Unable to fetch user info - connection timeout")
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP {response.status_code}: {response.text}"
        logger.error(f"Failed to get user info: {error_msg}")
        raise JiraOAuthError(f"Failed to retrieve user information: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error getting user info: {error_msg}")
        raise JiraOAuthError(f"Failed to retrieve user information: {error_msg}")


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


def create_state_with_provider(provider: str = 'jira') -> str:
    """
    Create a state parameter with provider information.
    
    Used to track which OAuth provider was used (jira or microsoft).
    Format: "provider:random_string"
    
    Args:
        provider: OAuth provider ('jira' or 'microsoft')
        
    Returns:
        State string with provider info
    """
    import secrets
    import base64
    
    # Generate random bytes and encode with provider
    random_bytes = secrets.token_bytes(16)
    random_string = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    
    return f"{provider}:{random_string}"


def extract_provider_from_state(state: str) -> str:
    """
    Extract the provider from a state parameter.
    
    Args:
        state: State parameter from OAuth callback (format: "provider:random_string")
        
    Returns:
        Provider name ('jira' or 'microsoft'), defaults to 'jira' if not found
    """
    if not state or ':' not in state:
        return 'jira'
    
    provider = state.split(':')[0]
    return provider if provider in ['jira', 'microsoft'] else 'jira'


def validate_oauth_config(oauth_config: Dict) -> Tuple[bool, str]:
    """
    Validate that OAuth configuration has all required fields.
    
    Args:
        oauth_config: OAuth configuration dictionary
        
    Returns:
        Tuple of (is_valid, message)
    """
    required_fields = [
        'client_id',
        'client_secret',
        'redirect_uri',
        'auth_url',
        'token_url',
        'resource_url',
        'scope'
    ]
    
    missing_fields = [field for field in required_fields if not oauth_config.get(field)]
    
    if missing_fields:
        error_msg = f"Missing OAuth configuration fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        return False, error_msg
    
    # Validate that URLs are properly formatted
    for url_field in ['redirect_uri', 'auth_url', 'token_url', 'resource_url']:
        url = oauth_config.get(url_field, '')
        if not url.startswith(('http://', 'https://')):
            error_msg = f"Invalid URL format for {url_field}: {url}"
            logger.error(error_msg)
            return False, error_msg
    
    logger.info("OAuth configuration is valid")
    return True, "OAuth configuration is valid"
