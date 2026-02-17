"""Jira Cloud API client and connection management."""

import streamlit as st
import logging
import os
from jira import JIRA

logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))  # API request timeout in seconds


@st.cache_resource
def get_jira_connection(url, email, api_token):
    """
    Establish and cache connection to Jira Cloud.
    Using st.cache_resource to maintain single connection throughout session.
    
    Args:
        url: Jira Cloud URL
        email: Jira account email
        api_token: Jira API token
        
    Returns:
        JIRA connection object or None if connection fails
    """
    try:
        # Initialize Jira connection with timeout for better performance
        jira = JIRA(
            server=url,
            basic_auth=(email, api_token),
            options={'timeout': REQUEST_TIMEOUT}
        )
        
        logger.info("Successfully connected to Jira")
        return jira
        
    except Exception as e:
        logger.error(f"Failed to connect to Jira: {str(e)}")
        return None


def validate_jira_connection(jira):
    """
    Test Jira connection and return validation result.
    
    Args:
        jira: Jira connection object
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if jira is None:
            return False, "Failed to establish Jira connection"
        
        # Try to get current user to validate connection
        jira.current_user()
        return True, "Connected to Jira successfully"
    
    except Exception as e:
        return False, f"Connection failed: {str(e)}"
