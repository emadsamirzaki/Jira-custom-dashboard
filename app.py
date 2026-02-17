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
import uuid
import tempfile
from pathlib import Path
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

# Session storage directory for persisting auth across page refreshes
SESSION_DIR = Path(tempfile.gettempdir()) / "streamlit_sessions"
SESSION_DIR.mkdir(exist_ok=True)

def get_session_file(session_id: str) -> Path:
    """Get path to session file for given session ID."""
    return SESSION_DIR / f"session_{session_id}.json"

def save_session(session_id: str, auth_data: dict):
    """Save authentication session to file."""
    try:
        session_file = get_session_file(session_id)
        with open(session_file, 'w') as f:
            json.dump(auth_data, f)
        logger.debug(f"Session saved: {session_id}")
    except Exception as e:
        logger.error(f"Error saving session: {e}")

def load_session(session_id: str) -> dict:
    """Load authentication session from file."""
    try:
        session_file = get_session_file(session_id)
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
            logger.debug(f"Session loaded: {session_id}")
            return data
    except Exception as e:
        logger.error(f"Error loading session: {e}")
    return None

def delete_session(session_id: str):
    """Delete authentication session file."""
    try:
        session_file = get_session_file(session_id)
        if session_file.exists():
            session_file.unlink()
        logger.debug(f"Session deleted: {session_id}")
    except Exception as e:
        logger.error(f"Error deleting session: {e}")

def create_session_id() -> str:
    """Generate a new session ID."""
    return str(uuid.uuid4())

# JavaScript for persisting auth data to cookies and checking restoration
PERSIST_AUTH_SCRIPT = """
<script>
// Set cookie helper
function setCookie(name, value, days = 30) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = "expires=" + d.toUTCString();
    document.cookie = name + "=" + encodeURIComponent(value) + ";" + expires + ";path=/;SameSite=Lax";
}

// Get cookie helper
function getCookie(name) {
    const nameEQ = name + "=";
    const cookies = document.cookie.split(';');
    for(let i = 0; i < cookies.length; i++) {
        let cookie = cookies[i].trim();
        if (cookie.indexOf(nameEQ) === 0) {
            return decodeURIComponent(cookie.substring(nameEQ.length));
        }
    }
    return null;
}

// Delete cookie helper
function deleteCookie(name) {
    setCookie(name, "", -1);
}

window.persistAuthData = function(data) {
    try {
        setCookie('jira_auth_token', data.access_token || '', 30);
        setCookie('jira_auth_user', JSON.stringify(data.user_info || {}), 30);
        setCookie('jira_auth_session', 'active', 30);
    } catch(e) {
        console.error('Error persisting auth:', e);
    }
};

window.getPersistedAuthData = function() {
    try {
        const token = getCookie('jira_auth_token');
        const user = getCookie('jira_auth_user');
        if (token && getCookie('jira_auth_session') === 'active') {
            return {
                access_token: token,
                user_info: user ? JSON.parse(user) : {}
            };
        }
    } catch(e) {
        console.error('Error restoring auth:', e);
    }
    return null;
};

window.clearPersistedAuthData = function() {
    deleteCookie('jira_auth_token');
    deleteCookie('jira_auth_user');
    deleteCookie('jira_auth_session');
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
    layout="wide",
    initial_sidebar_state="collapsed"  # Start with sidebar collapsed
)

# VERY AGGRESSIVE CSS to ensure sidebar is hidden on login
# This must be placed IMMEDIATELY after set_page_config
comprehensive_hide_style = """
    <style>
    /* Hide entire sidebar and all its contents */
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    .hide-sidebar [data-testid="stSidebar"],
    [role="complementary"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }
    
    /* Hide sidebar nav */
    [data-testid="stSidebar"] nav,
    [data-testid="stSidebar"] nav ~ * {
        display: none !important;
    }
    
    /* Hide any menu button or navigation links in sidebar */
    [data-testid="stSidebar"] [role="menuitem"],
    [data-testid="stSidebar"] [class*="menu"],
    [data-testid="stSidebar"] [class*="nav"] {
        display: none !important;
    }
    
    /* Ensure sidebar takes no space */
    [data-testid="stSidebar"][aria-hidden="true"] {
        display: none !important;
    }
    </style>
"""
st.markdown(comprehensive_hide_style, unsafe_allow_html=True)

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
    Persist authentication data to browser localStorage and file.
    This survives page refreshes within the same session.
    """
    if st.session_state.get('authenticated'):
        # Create or reuse session ID
        if not st.session_state.get('session_id'):
            st.session_state.session_id = create_session_id()
            
        session_id = st.session_state.session_id
        
        # Save auth data to file for recovery on refresh
        auth_data = {
            'authenticated': True,
            'access_token': st.session_state.get('access_token'),
            'refresh_token': st.session_state.get('refresh_token'),
            'user_info': st.session_state.get('user_info'),
            'token_expires_at': st.session_state.get('token_expires_at')
        }
        
        save_session(session_id, auth_data)
        
        # Add session ID to query params
        try:
            if 'session_id' not in get_query_params():
                st.query_params['session_id'] = session_id
        except:
            pass
        
        # JavaScript to persist to browser cookies
        st.markdown(f"""
            <script>
            window.persistAuthData({json.dumps(auth_data)});
            </script>
        """, unsafe_allow_html=True)
        logger.info(f"Auth data persisted - Session: {session_id}")


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
                # Delete session file
                if st.session_state.get('session_id'):
                    delete_session(st.session_state.session_id)
                
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
                st.session_state.session_id = None
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
    
    # Get query parameters
    query_params = get_query_params()
    
    # Initialize session state with defaults
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'oauth_code_processed' not in st.session_state:
        st.session_state.oauth_code_processed = False
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    
    # Try to restore from file-based session if we see session_id in query params
    if 'session_id' in query_params and not st.session_state.authenticated:
        session_id = query_params['session_id']
        session_data = load_session(session_id)
        
        if session_data:
            logger.info(f"Restoring session from file: {session_id}")
            st.session_state.authenticated = session_data.get('authenticated', False)
            st.session_state.access_token = session_data.get('access_token')
            st.session_state.refresh_token = session_data.get('refresh_token')
            st.session_state.user_info = session_data.get('user_info')
            st.session_state.token_expires_at = session_data.get('token_expires_at')
            st.session_state.session_id = session_id
    
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
    
    # Show sidebar CSS when authenticated
    if (oauth_enabled and st.session_state.authenticated) or not oauth_enabled:
        # Show the sidebar by removing the hiding CSS
        st.markdown("""
            <style>
            /* Restore sidebar visibility when authenticated */
            [data-testid="stSidebar"] {
                display: block !important;
                visibility: visible !important;
            }
            /* Keep nav hidden (Streamlit pages) */
            [data-testid="stSidebar"] nav {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        render_sidebar()
        logger.debug("Sidebar rendered (authenticated)")
    else:
        # Keep sidebar hidden during login
        st.markdown("""
            <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        logger.debug("Sidebar hidden (not authenticated)")
    
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

