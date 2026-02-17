"""Configuration loader from environment variables and config.yaml."""

import streamlit as st
import yaml
import os
import logging

logger = logging.getLogger(__name__)


def load_config():
    """
    Load Jira configuration from environment variables or config.yaml.
    Priority: Environment variables > config.yaml
    
    Environment variables:
    - JIRA_URL: Jira Cloud URL
    - JIRA_EMAIL: Jira account email
    - JIRA_TOKEN: Jira API token
    - JIRA_PROJECT_KEY: Project key
    - JIRA_BOARD_ID: Board ID
    """
    config = {
        'jira': {},
        'components': {'preferred_order': []}
    }
    
    # Try to load from environment variables first (recommended for production)
    jira_url = os.getenv('JIRA_URL', '').strip()
    jira_email = os.getenv('JIRA_EMAIL', '').strip()
    jira_token = os.getenv('JIRA_TOKEN', '').strip()
    jira_project_key = os.getenv('JIRA_PROJECT_KEY', '').strip()
    jira_board_id = os.getenv('JIRA_BOARD_ID', '').strip()
    
    # If all env vars are set, use them
    if jira_url and jira_email and jira_token and jira_project_key and jira_board_id:
        try:
            config['jira'] = {
                'url': jira_url.rstrip('/'),
                'email': jira_email,
                'api_token': jira_token,
                'project_key': jira_project_key,
                'board_id': int(jira_board_id)
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
