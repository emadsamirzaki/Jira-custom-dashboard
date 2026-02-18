"""Authentication module for OAuth 2.0 integration with Atlassian."""

from auth.oauth import (
    get_authorization_url,
    exchange_code_for_token,
    get_user_info,
    validate_user_belongs_to_workspace,
    refresh_access_token,
    validate_oauth_config,
    create_state_with_provider,
    extract_provider_from_state,
    JiraOAuthError
)

__all__ = [
    'get_authorization_url',
    'exchange_code_for_token',
    'get_user_info',
    'validate_user_belongs_to_workspace',
    'refresh_access_token',
    'validate_oauth_config',
    'create_state_with_provider',
    'extract_provider_from_state',
    'JiraOAuthError',
]
