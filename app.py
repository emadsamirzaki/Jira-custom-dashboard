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
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')  # Changed to INFO for debugging
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# JavaScript for persisting auth data to localStorage
PERSIST_AUTH_SCRIPT = """
<script>
window.persistAuthData = function(data) {
    localStorage.setItem('jira_dashboard_auth', JSON.stringify(data));
};

window.getPersistedAuthData = function() {
    const data = localStorage.getItem('jira_dashboard_auth');
    return data ? JSON.parse(data) : null;
};

window.clearPersistedAuthData = function() {
    localStorage.removeItem('jira_dashboard_auth');
};
</script>
"""

# Inject persistence script once
if 'auth_script_injected' not in st.session_state:
    st.markdown(PERSIST_AUTH_SCRIPT, unsafe_allow_html=True)
    st.session_state.auth_script_injected = True

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


# Compatibility wrapper for query_params access
def get_query_params():
    """Get query parameters with compatibility for different Streamlit versions."""
    try:
        return st.query_params
    except AttributeError:
        # Fallback for older Streamlit versions
        try:
            return st.experimental_get_query_params()
        except:
            return {}


def clear_query_params():
    """Clear query parameters with compatibility for different Streamlit versions."""
    try:
        st.query_params.clear()
    except AttributeError:
        pass


def persist_auth_to_browser():
    """
    Persist authentication data to browser localStorage.
    This survives page refreshes within the same session.
    """
    if st.session_state.get('authenticated'):
        auth_data = {
            'authenticated': True,
            'access_token': st.session_state.get('access_token'),
            'refresh_token': st.session_state.get('refresh_token'),
            'user_info': st.session_state.get('user_info'),
            'token_expires_at': st.session_state.get('token_expires_at')
        }
        
        # JavaScript to persist to localStorage
        st.markdown(f"""
            <script>
            window.persistAuthData({json.dumps(auth_data)});
            </script>
        """, unsafe_allow_html=True)
        logger.info("Auth data persisted to browser storage")


def restore_auth_from_browser():
    """
    Restore authentication data from browser localStorage if session was lost.
    """
    # Try to restore from browser storage via JavaScript
    st.markdown("""
        <script>
        const authData = window.getPersistedAuthData();
        if (authData && authData.authenticated) {
            // Signal to Python that we have auth data to restore
            window.authDataAvailable = authData;
        }
        </script>
    """, unsafe_allow_html=True)
    
    # For now, we'll manually check via session state
    # In a real scenario, we'd use st_javascript or similar
    # For simplicity, we trust Streamlit's session state persistence
    return None


def handle_oauth_callback(oauth_config: dict, jira_config: dict):
    """
    Handle OAuth 2.0 callback from Atlassian.
    
    Checks query params for auth code and exchanges it for token.
    Only processes if not already authenticated.
    """
    # If already authenticated, don't reprocess the callback
    if st.session_state.get('authenticated'):
        logger.info("Already authenticated, skipping OAuth callback processing")
        return False
    
    query_params = get_query_params()
    
    if 'code' not in query_params:
        logger.info("No auth code in query params")
        return False
    
    auth_code = query_params['code']
    logger.info(f"Received auth code: {auth_code[:20]}...")
    
    try:
        # Show loading spinner
        with st.spinner("Authenticating with Atlassian..."):
            logger.info("Starting token exchange...")
            # Exchange auth code for access token
            token_data = exchange_code_for_token(auth_code, oauth_config)
            logger.info("Token exchange successful")
            
            # Get user information
            access_token = token_data.get('access_token')
            logger.info("Exchanging token for user info...")
            user_info = get_user_info(access_token, oauth_config)
            logger.info(f"User info retrieved: {user_info}")
            
            # Validate user belongs to workspace
            is_valid, validation_msg = validate_user_belongs_to_workspace(
                user_info, jira_config
            )
            
            if not is_valid:
                st.error(f"❌ {validation_msg}")
                st.error("Access restricted to wkengineering Jira users only")
                st.stop()
            
            # Store auth data in session state BEFORE clearing query params
            st.session_state.authenticated = True
            st.session_state.access_token = access_token
            st.session_state.refresh_token = token_data.get('refresh_token')
            st.session_state.user_info = user_info
            st.session_state.token_expires_at = None
            
            # Persist auth to browser storage for page refresh resilience
            persist_auth_to_browser()
            
            logger.info(f"User {user_info.get('email')} authenticated successfully")
            st.success("✅ Successfully logged in!")
            
            # Clear query params and reload URL cleanly
            try:
                # Try to clear modern query params
                st.query_params.clear()
            except:
                pass
            
            # Use JavaScript to clean the URL in browser history
            st.markdown("""
                <script>
                window.history.replaceState({}, document.title, window.location.pathname);
                </script>
            """, unsafe_allow_html=True)
            
            # Brief pause before rerun to ensure params are cleared
            import time
            time.sleep(0.5)
            st.rerun()
        
    except JiraOAuthError as e:
        error_msg = str(e)
        logger.error(f"OAuth callback error: {error_msg}")
        st.error(f"❌ Authentication Error: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error in OAuth callback: {error_msg}")
        st.error(f"❌ Unexpected error during authentication: {error_msg}")


def render_user_menu_top_right():
    """Render compact user menu in top right corner like Jira."""
    user_info = st.session_state.get('user_info', {})
    
    if not user_info:
        return
    
    name = user_info.get('name', 'User')
    email = user_info.get('email', 'N/A')
    picture = user_info.get('picture')
    
    # Create top right menu using columns
    col_spacer, col_menu = st.columns([4, 1])
    
    with col_menu:
        # Expandable menu in top right
        with st.expander("👤", expanded=False):
            st.markdown(f"**{name}**")
            st.caption(email)
            
            if picture:
                st.image(picture, width=80)
            
            st.divider()
            
            if st.button("🚪 Logout", use_container_width=True, key="logout_btn_top"):
                # Clear browser localStorage
                st.markdown("""
                    <script>
                    window.clearPersistedAuthData();
                    </script>
                """, unsafe_allow_html=True)
                
                # Clear all session state
                st.session_state.authenticated = False
                st.session_state.access_token = None
                st.session_state.refresh_token = None
                st.session_state.user_info = None
                st.session_state.current_page = 'Home'
                st.session_state.selected_component = None
                st.session_state.oauth_code_processed = False  # Reset for next login
                st.rerun()


def render_user_menu():
    """Legacy function - consolidated into render_user_menu_top_right()."""
    pass


def main():
    """Main application logic - routes pages based on authentication and session state."""
    
    # Load configuration
    config = load_config()
    oauth_config = config.get('oauth', {})
    jira_config = config.get('jira', {})
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'oauth_code_processed' not in st.session_state:
        st.session_state.oauth_code_processed = False
    
    # Try to restore auth from browser storage on page load/refresh
    # Add script to check localStorage and restore if available
    if not st.session_state.authenticated:
        st.markdown("""
            <script>
            function restoreAuth() {
                const authData = window.getPersistedAuthData();
                if (authData && authData.authenticated) {
                    // Signal to reload with auth restored
                    sessionStorage.setItem('authRestored', 'true');
                }
            }
            restoreAuth();
            </script>
        """, unsafe_allow_html=True)
    
    # Check if OAuth is enabled
    oauth_enabled = oauth_config.get('enabled', False)
    
    # Handle OAuth callback if present
    query_params = get_query_params()
    
    # If already authenticated but URL still has code param, immediately redirect to clean URL
    if oauth_enabled and st.session_state.authenticated and 'code' in query_params:
        logger.info("Already authenticated with code in URL - redirecting to clean URL")
        
        # Use JavaScript to redirect to clean URL
        st.markdown("""
            <script>
            if (window.location.search) {
                window.location.replace(window.location.pathname);
            }
            </script>
        """, unsafe_allow_html=True)
        return
    
    # Handle OAuth callback if present AND not already authenticated
    if oauth_enabled and not st.session_state.authenticated and 'code' in query_params:
        if not st.session_state.oauth_code_processed:
            handle_oauth_callback(oauth_config, jira_config)
            st.session_state.oauth_code_processed = True
    
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
    
    # Persist auth to browser on every render if authenticated (survival across refresh)
    if oauth_enabled and st.session_state.authenticated:
        persist_auth_to_browser()
    
    # Render user menu in top right if OAuth authenticated
    if oauth_enabled and st.session_state.authenticated:
        render_user_menu_top_right()
    
    # Render sidebar navigation only if authenticated
    if st.session_state.authenticated or not oauth_enabled:
        render_sidebar()
    
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

