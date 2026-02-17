"""Sidebar navigation component for dashboard."""

import streamlit as st
from datetime import datetime
from config.loader import load_config
from jira_integration.client import get_jira_connection
from jira_integration.queries import get_project_components
from ui.branding import display_sidebar_branding


def render_sidebar():
    """
    Render the sidebar with navigation menu and component selection.
    Updates session state based on selected pages.
    """
    with st.sidebar:
        # Display company branding at the top of sidebar
        display_sidebar_branding()
        
        st.divider()
        
        st.header("📊 Navigation")
        
        # Navigation menu with session state management
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'Home'
        
        if 'selected_component' not in st.session_state:
            st.session_state.selected_component = None
        
        if 'last_updated_time' not in st.session_state:
            st.session_state.last_updated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Main page selection
        main_pages = ['Home', 'Sprint Status', 'Component Capability Status', 'Sprint Metrics', 'Custom Reports']
        current_index = main_pages.index(st.session_state.current_page.split(' - ')[0]) if st.session_state.current_page.split(' - ')[0] in main_pages else 0
        
        selected_main = st.radio(
            "Select a page:",
            main_pages,
            index=current_index,
            key='nav_menu'
        )
        
        # If "Sprint Status" is selected, show component submenu
        if selected_main == 'Sprint Status':
            st.divider()
            st.subheader("📋 Select Component")
            
            # Load config for Jira connection (needed for component fetching)
            config = load_config()
            jira_config = config.get('jira', {})
            
            try:
                jira_conn = get_jira_connection(
                    jira_config['url'],
                    jira_config['email'],
                    jira_config['api_token']
                )
                
                if jira_conn:
                    # Define preferred component order (will match by keyword)
                    preferred_order = config.get('components', {}).get('preferred_order', [])
                    
                    components = get_project_components(jira_conn, jira_config['project_key'], preferred_order)
                    
                    if components:
                        selected_component = st.selectbox(
                            "Choose component:",
                            components,
                            key='component_select'
                        )
                        st.session_state.selected_component = selected_component
                        st.session_state.current_page = f'Sprint Status - {selected_component}'
                    else:
                        st.warning("No components found in project")
                        st.session_state.current_page = 'Home'
                else:
                    st.warning("Unable to fetch components")
                    st.session_state.current_page = 'Home'
            
            except Exception as e:
                st.warning(f"Error loading components: {str(e)}")
                st.session_state.current_page = 'Home'
        
        # If "Component Capability Status" is selected, show component submenu
        elif selected_main == 'Component Capability Status':
            st.divider()
            st.subheader("📋 Select Component")
            
            # Load config for Jira connection (needed for component fetching)
            config = load_config()
            jira_config = config.get('jira', {})
            
            try:
                jira_conn = get_jira_connection(
                    jira_config['url'],
                    jira_config['email'],
                    jira_config['api_token']
                )
                
                if jira_conn:
                    # Define preferred component order (will match by keyword)
                    preferred_order = config.get('components', {}).get('preferred_order', [])
                    
                    components = get_project_components(jira_conn, jira_config['project_key'], preferred_order)
                    
                    if components:
                        selected_component = st.selectbox(
                            "Choose component:",
                            components,
                            key='capability_component_select'
                        )
                        st.session_state.selected_component = selected_component
                        st.session_state.current_page = f'Component Capability Status - {selected_component}'
                    else:
                        st.warning("No components found in project")
                        st.session_state.current_page = 'Home'
                else:
                    st.warning("Unable to fetch components")
                    st.session_state.current_page = 'Home'
            
            except Exception as e:
                st.warning(f"Error loading components: {str(e)}")
                st.session_state.current_page = 'Home'
        
        else:
            st.session_state.current_page = selected_main
            st.session_state.selected_component = None
        
        st.divider()
        st.subheader("About")
        st.info("Simple Jira Cloud dashboard for tracking project and sprint information.")
