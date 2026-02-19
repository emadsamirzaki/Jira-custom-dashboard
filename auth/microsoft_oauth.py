"""OAuth 2.0 authentication logic for Microsoft Entra ID (Azure AD)."""

import logging
import requests
import urllib.parse
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class MicrosoftOAuthError(Exception):
    """Custom exception for Microsoft OAuth errors."""
    pass


def get_microsoft_authorization_url(microsoft_config: Dict, state: str = None) -> str:
    """
    Generate the authorization URL for Microsoft OAuth flow.
    
    Args:
        microsoft_config: Microsoft OAuth configuration dictionary
        state: Optional state parameter for CSRF protection
        
    Returns:
        Authorization URL to redirect user to
        
    Raises:
        MicrosoftOAuthError: If configuration is invalid
    """
    try:
        tenant_id = microsoft_config.get('tenant_id')
        client_id = microsoft_config.get('client_id')
        redirect_uri = microsoft_config.get('redirect_uri')
        scope = microsoft_config.get('scope', 'openid profile email User.Read')
        
        if not all([tenant_id, client_id, redirect_uri]):
            raise MicrosoftOAuthError("Missing required Microsoft configuration")
        
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': scope,
            'response_mode': 'query',
        }
        
        if state:
            params['state'] = state
        
        auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        full_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
        
        logger.info(f"Generated Microsoft OAuth URL for tenant: {tenant_id}")
        
        return full_url
        
    except Exception as e:
        logger.error(f"Error generating Microsoft auth URL: {str(e)}")
        raise MicrosoftOAuthError(f"Failed to generate authentication URL: {str(e)}")


def exchange_microsoft_code_for_token(
    auth_code: str,
    microsoft_config: Dict
) -> Dict:
    """
    Exchange authorization code for Microsoft access token.
    
    Args:
        auth_code: Authorization code from Microsoft OAuth callback
        microsoft_config: Microsoft OAuth configuration dictionary
        
    Returns:
        Dictionary containing access_token, refresh_token, expires_in, etc.
        
    Raises:
        MicrosoftOAuthError: If token exchange fails
    """
    try:
        tenant_id = microsoft_config.get('tenant_id')
        client_id = microsoft_config.get('client_id')
        client_secret = microsoft_config.get('client_secret')
        redirect_uri = microsoft_config.get('redirect_uri')
        
        if not all([tenant_id, client_id, client_secret, redirect_uri]):
            raise MicrosoftOAuthError("Missing required Microsoft configuration")
        
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'client_secret': client_secret,
            'code': auth_code,
            'redirect_uri': redirect_uri,
            'scope': microsoft_config.get('scope', 'openid profile email User.Read'),
        }
        
        logger.info(f"Attempting Microsoft token exchange at: {token_url}")
        logger.debug(f"Token request data: grant_type={data['grant_type']}, client_id={data['client_id'][:10]}..., redirect_uri={data['redirect_uri']}")
        
        response = requests.post(token_url, data=data, timeout=10)
        
        logger.debug(f"Microsoft token exchange response status: {response.status_code}")
        logger.debug(f"Microsoft token exchange response text: {response.text[:500]}")
        
        response.raise_for_status()
        
        token_data = response.json()
        logger.info("Successfully exchanged Microsoft auth code for access token")
        return token_data
        
    except requests.exceptions.Timeout:
        raise MicrosoftOAuthError("Authentication timeout - unable to connect to Microsoft")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Microsoft token exchange failed: {e}")
        try:
            error_data = response.json()
        except:
            error_data = {}
        error_code = error_data.get('error', 'unknown_error')
        error_desc = error_data.get('error_description', str(e))
        logger.error(f"Microsoft error code: {error_code}, description: {error_desc}")
        raise MicrosoftOAuthError(f"Login failed: {error_desc}")
    except Exception as e:
        logger.error(f"Unexpected error during Microsoft token exchange: {str(e)}")
        raise MicrosoftOAuthError(f"Login failed: {str(e)}")


def get_microsoft_user_info(access_token: str) -> Dict:
    """
    Get user information from Microsoft Graph API including photo.
    
    Args:
        access_token: Microsoft OAuth access token
        
    Returns:
        Dictionary with user info (displayName, mail, userPrincipalName, id, photo, etc.)
        
    Raises:
        MicrosoftOAuthError: If user info retrieval fails
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        }
        
        # Get user profile from Microsoft Graph
        resource_url = "https://graph.microsoft.com/v1.0/me"
        logger.info(f"Requesting Microsoft user info from: {resource_url}")
        
        response = requests.get(resource_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        user_info = response.json()
        
        logger.info(f"Successfully retrieved Microsoft user info: {user_info.get('displayName')}")
        
        # Try to get user photo as base64 data URL
        try:
            photo_url = "https://graph.microsoft.com/v1.0/me/photo/$value"
            photo_response = requests.get(photo_url, headers=headers, timeout=10)
            
            if photo_response.status_code == 200:
                import base64
                photo_data = base64.b64encode(photo_response.content).decode('utf-8')
                photo_mime = photo_response.headers.get('content-type', 'image/jpeg')
                user_info['picture'] = f"data:{photo_mime};base64,{photo_data}"
                logger.info("Successfully retrieved Microsoft user photo")
            else:
                logger.debug(f"Photo not available for user: {photo_response.status_code}")
                user_info['picture'] = None
                
        except Exception as photo_error:
            logger.debug(f"Could not retrieve user photo: {str(photo_error)}")
            user_info['picture'] = None
        
        return user_info
        
    except requests.exceptions.Timeout:
        logger.error("Microsoft user info request timeout")
        raise MicrosoftOAuthError("Unable to fetch user info - connection timeout")
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP {response.status_code}: {response.text}"
        logger.error(f"Failed to get Microsoft user info: {error_msg}")
        raise MicrosoftOAuthError(f"Failed to retrieve user information: {error_msg}")
    except Exception as e:
        logger.error(f"Unexpected error getting Microsoft user info: {str(e)}")
        raise MicrosoftOAuthError(f"Failed to retrieve user information: {str(e)}")


def refresh_microsoft_token(
    refresh_token: str,
    microsoft_config: Dict
) -> Dict:
    """
    Refresh an expired Microsoft access token.
    
    Args:
        refresh_token: Microsoft refresh token from previous auth
        microsoft_config: Microsoft OAuth configuration dictionary
        
    Returns:
        Dictionary with new access_token and expires_in
        
    Raises:
        MicrosoftOAuthError: If token refresh fails
    """
    try:
        tenant_id = microsoft_config.get('tenant_id')
        client_id = microsoft_config.get('client_id')
        client_secret = microsoft_config.get('client_secret')
        
        if not all([tenant_id, client_id, client_secret]):
            raise MicrosoftOAuthError("Missing required Microsoft configuration")
        
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'scope': 'openid profile email User.Read',
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        logger.info("Successfully refreshed Microsoft access token")
        return token_data
        
    except requests.exceptions.HTTPError:
        logger.error("Microsoft token refresh failed - session may have expired")
        raise MicrosoftOAuthError("Session expired - please login again")
    except Exception as e:
        logger.error(f"Error refreshing Microsoft token: {str(e)}")
        raise MicrosoftOAuthError("Failed to refresh session")


def validate_microsoft_user(user_info: Dict, microsoft_config: Dict) -> tuple[bool, str]:
    """
    Validate that Microsoft user is valid.
    Can optionally check for specific domain or organizational requirements.
    
    Args:
        user_info: User information from Microsoft Graph
        microsoft_config: Microsoft configuration dictionary
        
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        display_name = user_info.get('displayName', 'Unknown')
        principal_name = user_info.get('userPrincipalName', '')
        mail = user_info.get('mail', '')
        
        # Check if user has required properties
        if not principal_name and not mail:
            return False, "Unable to determine user email"
        
        logger.info(f"Validating Microsoft user: {display_name} ({principal_name or mail})")
        
        # Optional: Check for specific domain or organization
        # For example, only allow @wkengineering.com users:
        # allowed_domain = microsoft_config.get('allowed_domain')
        # if allowed_domain and not principal_name.endswith(f"@{allowed_domain}"):
        #     return False, f"User must belong to {allowed_domain} domain"
        
        return True, f"Access granted for {display_name}"
        
    except Exception as e:
        logger.error(f"Error validating Microsoft user: {str(e)}")
        return False, f"Failed to validate user: {str(e)}"


def is_microsoft_token_expired(token_data: Optional[Dict]) -> bool:
    """
    Check if Microsoft token is expired or invalid.
    
    Args:
        token_data: Token data dictionary with expires_in or expiry timestamp
        
    Returns:
        True if token is expired or invalid, False if still valid
    """
    if not token_data or 'access_token' not in token_data:
        return True
    
    # Token data from Microsoft includes 'expires_in' (seconds from now)
    # In a real scenario, you'd want to store expiry timestamp and check it
    # For now, we consider any token_data with access_token as valid
    # The stored token info should track expiry time
    
    return False
