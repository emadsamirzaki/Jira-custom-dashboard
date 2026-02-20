"""Configuration loader from environment variables and config.yaml."""

import streamlit as st
import yaml
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file if it exists
load_dotenv()


def load_config():
    """
    Load Jira configuration from environment variables or config.yaml.
    Priority: Environment variables (.env) > config.yaml > defaults
    
    Environment variables (.env file):
    - JIRA_URL: Jira Cloud URL
    - JIRA_EMAIL: Jira account email
    - JIRA_API_TOKEN: Jira API token
    - JIRA_PROJECT_KEY: Project key
    - JIRA_BOARD_ID: Board ID
    - JIRA_OAUTH_ENABLED: Enable Jira OAuth
    - JIRA_CLIENT_ID: Jira OAuth client ID
    - JIRA_CLIENT_SECRET: Jira OAuth client secret
    - MICROSOFT_OAUTH_ENABLED: Enable Microsoft OAuth
    - MICROSOFT_CLIENT_ID: Microsoft OAuth client ID
    - MICROSOFT_CLIENT_SECRET: Microsoft OAuth client secret
    - MICROSOFT_TENANT_ID: Microsoft tenant ID
    """
    config = {
        'jira': {},
        'oauth': {},
        'microsoft': {},
        'components': {'preferred_order': []}
    }
    
    # Try to load OAuth and Jira config from environment variables first (recommended for production)
    # Jira OAuth Configuration
    jira_oauth_enabled = os.getenv('JIRA_OAUTH_ENABLED', '').lower() == 'true'
    jira_client_id = os.getenv('JIRA_CLIENT_ID', '').strip()
    jira_client_secret = os.getenv('JIRA_CLIENT_SECRET', '').strip()
    jira_redirect_uri = os.getenv('JIRA_REDIRECT_URI', '').strip()
    
    # Microsoft OAuth Configuration
    microsoft_oauth_enabled = os.getenv('MICROSOFT_OAUTH_ENABLED', '').lower() == 'true'
    microsoft_client_id = os.getenv('MICROSOFT_CLIENT_ID', '').strip()
    microsoft_client_secret = os.getenv('MICROSOFT_CLIENT_SECRET', '').strip()
    microsoft_tenant_id = os.getenv('MICROSOFT_TENANT_ID', '').strip()
    microsoft_redirect_uri = os.getenv('MICROSOFT_REDIRECT_URI', '').strip()
    
    # Jira API Configuration
    jira_url = os.getenv('JIRA_URL', '').strip()
    jira_email = os.getenv('JIRA_EMAIL', '').strip()
    jira_api_token = os.getenv('JIRA_API_TOKEN', '').strip()
    jira_project_key = os.getenv('JIRA_PROJECT_KEY', '').strip()
    jira_board_id = os.getenv('JIRA_BOARD_ID', '').strip()
    jira_allowed_instance = os.getenv('JIRA_ALLOWED_INSTANCE', '').strip()
    
    # If env vars are set, use them
    if jira_url and jira_email and jira_api_token and jira_project_key and jira_board_id:
        try:
            config['jira'] = {
                'url': jira_url.rstrip('/'),
                'email': jira_email,
                'api_token': jira_api_token,
                'project_key': jira_project_key,
                'board_id': int(jira_board_id),
                'allowed_instance': jira_allowed_instance
            }
            
            # Add OAuth configuration if present
            if jira_oauth_enabled and jira_client_id and jira_client_secret:
                config['oauth'] = {
                    'enabled': True,
                    'jira': {
                        'enabled': True,
                        'client_id': jira_client_id,
                        'client_secret': jira_client_secret,
                        'redirect_uri': jira_redirect_uri,
                        'scope': os.getenv('JIRA_SCOPE', 'read:me read:jira-work read:jira-user offline_access'),
                        'auth_url': os.getenv('JIRA_AUTH_URL', 'https://auth.atlassian.com/authorize'),
                        'token_url': os.getenv('JIRA_TOKEN_URL', 'https://auth.atlassian.com/oauth/token'),
                        'resource_url': os.getenv('JIRA_RESOURCE_URL', 'https://api.atlassian.com/me')
                    }
                }
            
            # Add Microsoft OAuth configuration if present
            if microsoft_oauth_enabled and microsoft_client_id and microsoft_client_secret:
                config['microsoft'] = {
                    'enabled': True,
                    'client_id': microsoft_client_id,
                    'client_secret': microsoft_client_secret,
                    'tenant_id': microsoft_tenant_id,
                    'redirect_uri': microsoft_redirect_uri,
                    'scope': os.getenv('MICROSOFT_SCOPE', 'openid profile email User.Read')
                }
            
            return config
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid environment variables: {str(e)}")
            # Fall through to config.yaml
    
    # Fallback to config.yaml file
    config_path = "config.yaml"
    
    if not os.path.exists(config_path):
        st.error(
            "❌ Configuration not found!\n\n"
            "Please either:\n"
            "1. Create a `.env` file with your Jira credentials (recommended for production)\n"
            "2. Create a `config.yaml` file with your Jira details\n\n"
            "See `.env.example` or `config.example.yaml` for templates."
        )
        st.stop()
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            # Normalize URL (remove trailing slash)
            if config.get('jira', {}).get('url'):
                config['jira']['url'] = config['jira']['url'].rstrip('/')
        return config
    except Exception as e:
        st.error(f"❌ Error loading configuration: {str(e)}")
        st.stop()
