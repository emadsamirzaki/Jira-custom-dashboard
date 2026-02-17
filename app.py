"""
Jira Dashboard - Main Application Entry Point
A simple Streamlit application to connect with Jira Cloud and display
project and sprint information with component capability metrics.

This is a refactored modular version with clean separation of concerns.
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

# Import modular components
from config.loader import load_config
from components.sidebar import render_sidebar
from ui.branding import display_branded_header, display_branded_footer
from pages.home import render_home_page
from pages.sprint_status import render_sprint_status_page
from pages.component_capability import render_component_capability_page
from pages.sprint_metrics import render_sprint_metrics_page
from pages.custom_reports import render_custom_reports_page


def main():
    """Main application logic - routes pages based on session state."""
    
    # Load configuration
    config = load_config()
    jira_config = config.get('jira', {})
    
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
    
    # Render sidebar navigation
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
