"""
Jira Dashboard - Main Application Entry Point
A simple Streamlit application to connect with Jira Cloud and display
project and sprint information with component capability metrics.

This is a refactored modular version with clean separation of concerns.
Supports OAuth 2.0 authentication with Atlassian.
"""

import streamlit as st
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'WARNING')
logging.basicConfig(
    level=getattr(logging, log_level, logging.WARNING),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Jira Dashboard | Wolters Kluwer",
    page_icon="📊",
    layout="wide"
)

# Hide Streamlit's default pages explorer in the sidebar for cleaner UI
# Keep logout button and other sidebar elements visible
hide_streamlit_style = """
    <style>
    /* Hide the nav element that contains page list */
    [data-testid="stSidebar"] nav {
        display: none !important;
    }
    /* Hide the elements after nav that are part of pages explorer */
    [data-testid="stSidebar"] nav ~ * {
        display: none !important;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Import modular components and auth
from config.loader import load_config
from components.sidebar import render_sidebar
from ui.branding import display_branded_header, display_branded_footer
from pages.home import render_home_page
from pages.sprint_status import render_sprint_status_page
from pages.component_capability import render_component_capability_page
from pages.sprint_metrics import render_sprint_metrics_page
from pages.custom_reports import render_custom_reports_page
from auth import (
    exchange_code_for_token,
    get_user_info,
    validate_user_belongs_to_workspace,
    JiraOAuthError
)
from auth.login import render_login_page


def handle_oauth_callback(oauth_config: dict, jira_config: dict):
    """
    Handle OAuth 2.0 callback from Atlassian.
    
    Checks st.query_params for auth code and exchanges it for token.
    """
    if 'code' not in st.query_params:
        return False
    
    auth_code = st.query_params['code']
    
    try:
        # Show loading spinner
        with st.spinner("Authenticating with Atlassian..."):
            # Exchange auth code for access token
            token_data = exchange_code_for_token(auth_code, oauth_config)
            
            # Get user information
            access_token = token_data.get('access_token')
            user_info = get_user_info(access_token, oauth_config)
            
            # Validate user belongs to workspace
            is_valid, validation_msg = validate_user_belongs_to_workspace(
                user_info, jira_config
            )
            
            if not is_valid:
                st.error(f"❌ {validation_msg}")
                st.error("Access restricted to wkengineering Jira users only")
                st.stop()
            
            # Store auth data in session state
            st.session_state.authenticated = True
            st.session_state.access_token = access_token
            st.session_state.refresh_token = token_data.get('refresh_token')
            st.session_state.user_info = user_info
            st.session_state.token_expires_at = None  # Implement expiry tracking if needed
            
            logger.info(f"User {user_info.get('email')} authenticated successfully")
            
        # Clear query params to prevent reprocessing
        st.query_params.clear()
        st.rerun()
        
    except JiraOAuthError as e:
        st.error(f"❌ Authentication Error: {str(e)}")
        logger.error(f"OAuth callback error: {str(e)}")
    except Exception as e:
        st.error(f"❌ Unexpected error during authentication: {str(e)}")
        logger.error(f"Unexpected error in OAuth callback: {str(e)}")


def render_logout_button():
    """Render logout button in sidebar."""
    if st.sidebar.button("🚪 Logout", key="logout_button"):
        # Clear all session state
        st.session_state.authenticated = False
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.session_state.user_info = None
        st.session_state.current_page = 'Home'
        st.session_state.selected_component = None
        st.rerun()


def render_user_info_sidebar():
    """Render user information and avatar in sidebar."""
    user_info = st.session_state.get('user_info', {})
    
    if user_info:
        st.sidebar.divider()
        st.sidebar.markdown("### 👤 User Info")
        
        # Display user name
        name = user_info.get('name', 'User')
        email = user_info.get('email', 'N/A')
        
        st.sidebar.markdown(f"**{name}**")
        st.sidebar.caption(email)
        
        # Display avatar if available
        if user_info.get('picture'):
            st.sidebar.image(user_info.get('picture'), width=50)


def main():
    """Main application logic - routes pages based on authentication and session state."""
    
    # Load configuration
    config = load_config()
    oauth_config = config.get('oauth', {})
    jira_config = config.get('jira', {})
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Check if OAuth is enabled
    oauth_enabled = oauth_config.get('enabled', False)
    
    # Handle OAuth callback if present
    if oauth_enabled and 'code' in st.query_params:
        handle_oauth_callback(oauth_config, jira_config)
    
    # Redirect to login if OAuth enabled and not authenticated
    if oauth_enabled and not st.session_state.authenticated:
        render_login_page(oauth_config, jira_config)
        return
    
    # If OAuth disabled, fall back to config-based authentication
    if not oauth_enabled:
        # Validate configuration completeness
        required_fields = ['url', 'email', 'api_token', 'project_key', 'board_id']
        missing_fields = [
            f for f in required_fields 
            if not jira_config.get(f) or jira_config.get(f) in [
                'your-domain.atlassian.net', 'your-email@example.com', 
                'your-api-token-here', 'MYPROJECT'
            ]
        ]
        
        if missing_fields:
            st.error(f"""
            ❌ Configuration incomplete. Please update config.yaml with your Jira details:
            
            Missing or placeholder values: {', '.join(missing_fields)}
            
            See README.md for instructions on how to find these values.
            """)
            st.stop()
    
    # === DASHBOARD RENDERING (for authenticated users or config-based auth) ===
    
    # Render sidebar navigation
    render_sidebar()
    
    # Render user info if OAuth authenticated
    if oauth_enabled and st.session_state.authenticated:
        render_user_info_sidebar()
        render_logout_button()
    
    # Get current page from session state
    current_page = st.session_state.get('current_page', 'Home')
    selected_component = st.session_state.get('selected_component', None)
    
    # Determine page title
    try:
        base_page_name = current_page.split(' - ')[0]
        page_title_map = {
            'Home': '📊 Jira Dashboard',
            'Sprint Status': f'🏃 Sprint Status - {selected_component}',
            'Component Capability Status': f'📈 Component Capability Status - {selected_component}',
            'Sprint Metrics': '📉 Sprint Metrics',
            'Custom Reports': '📋 Custom Reports'
        }
        page_title = page_title_map.get(base_page_name, '📊 Jira Dashboard')
    except Exception as e:
        logger.warning(f"Error determining page title: {str(e)}")
        page_title = '📊 Jira Dashboard'
    
    # Display branded header
    display_branded_header(page_title)
    
    # Route to appropriate page
    if current_page == 'Home':
        render_home_page(jira_config)
    
    elif current_page.startswith('Sprint Status - '):
        render_sprint_status_page(jira_config, selected_component)
    
    elif current_page.startswith('Component Capability Status - '):
        render_component_capability_page(jira_config, selected_component)
    
    elif current_page == 'Sprint Metrics':
        render_sprint_metrics_page()
    
    elif current_page == 'Custom Reports':
        render_custom_reports_page()
    
    # Display branded footer
    display_branded_footer()


# Run application
if __name__ == "__main__":
    main()

