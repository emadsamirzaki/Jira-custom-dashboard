"""Home page showing project and sprint overview."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging

from jira_integration.client import get_jira_connection, validate_jira_connection
from jira_integration.queries import (
    get_project_info, get_active_sprint, get_components_issues_count,
    get_release_versions
)
from jira_integration.data_processor import is_date_past
from ui.utils import display_refresh_button

logger = logging.getLogger(__name__)


def render_home_page(jira_config):
    """Render the home page with project and sprint information."""
    
    # Display refresh button with last updated time
    display_refresh_button()
    
    st.divider()
    
    # Connect to Jira
    with st.spinner("Connecting to Jira..."):
        jira = get_jira_connection(
            jira_config['url'],
            jira_config['email'],
            jira_config['api_token']
        )
    
    # Validate connection
    is_connected, message = validate_jira_connection(jira)
    
    if not is_connected:
        st.error(f"❌ {message}")
        st.warning("""
        Please verify your Jira configuration in config.yaml:
        - Check the URL format
        - Check email address
        - Regenerate API token if needed
        - Ensure project key and board ID are correct
        """)
        return
    
    st.success("✅ " + message)
    st.divider()
    
    # Display Project Information
    st.subheader("📋 Project Information")
    
    with st.spinner("Fetching project information..."):
        project_info = get_project_info(jira, jira_config['project_key'])
    
    if project_info:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Project Name", project_info['name'])
            st.metric("Project Key", project_info['key'])
        with col2:
            st.text_area(
                "Project Description",
                value=project_info['description'],
                height=200,
                disabled=True
            )
    else:
        st.error("Failed to retrieve project information")
        return
    
    st.divider()
    
    # Display Sprint Information
    st.subheader("🏃 Active Sprint Information")
    
    with st.spinner("Fetching sprint information..."):
        sprint_info = get_active_sprint(jira, jira_config['board_id'])
    
    if sprint_info:
        col1, spacer1, col2, col3, col4 = st.columns([1.2, 0.3, 1.5, 1.5, 1.5])
        
        with col1:
            st.metric("Sprint Name", sprint_info['name'])
        
        with spacer1:
            pass  # Spacer column
        
        with col2:
            start_date = sprint_info['start_date']
            if isinstance(start_date, str) and start_date != 'Not set':
                # Parse and format date
                try:
                    date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    start_date = date_obj.strftime('%Y-%m-%d')
                except:
                    pass
            st.metric("Sprint Start Date", start_date)
        
        with col3:
            end_date = sprint_info['end_date']
            if isinstance(end_date, str) and end_date != 'Not set':
                # Parse and format date
                try:
                    date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    end_date = date_obj.strftime('%Y-%m-%d')
                except:
                    pass
            st.metric("Sprint End Date", end_date)
        
        with col4:
            # Calculate remaining working days (excluding weekends)
            remaining_days = "N/A"
            if isinstance(sprint_info['end_date'], str) and sprint_info['end_date'] != 'Not set':
                try:
                    end_date_obj = datetime.fromisoformat(sprint_info['end_date'].replace('Z', '+00:00'))
                    today = datetime.now(end_date_obj.tzinfo).date()
                    end_date_only = end_date_obj.date()
                    
                    # Count working days (Monday=0 to Friday=4)
                    working_days = 0
                    current = today
                    while current <= end_date_only:
                        if current.weekday() < 5:  # Monday to Friday
                            working_days += 1
                        current += timedelta(days=1)
                    
                    remaining_days = str(working_days)
                except:
                    pass
            st.metric("Working Days Remaining", remaining_days)
        
        st.write("")  # Extra spacing
        st.divider()
        st.write("")  # Extra spacing
        st.info(f"Sprint State: **{sprint_info['state']}**")
        st.write("")  # Extra spacing
    
    else:
        st.warning("No active sprint found. Create a sprint in Jira or check the board ID in config.yaml")
    
    st.divider()
    
    # Display Components and Issues Count (Current Sprint)
    st.subheader("📦 Issues by Component (Current Sprint)")
    
    if sprint_info:
        with st.spinner("Fetching component issues..."):
            components_data = get_components_issues_count(jira, jira_config['project_key'], sprint_info['id'])
        
        if components_data:
            # Convert to DataFrame for better table display
            df = pd.DataFrame(components_data)
            
            # Display as a formatted table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Component": st.column_config.TextColumn("Component", width="medium"),
                    "# Story/Task": st.column_config.NumberColumn("# Story/Task", format="%d"),
                    "# Bugs": st.column_config.NumberColumn("# Bugs", format="%d"),
                    "Total": st.column_config.NumberColumn("Total", format="%d")
                }
            )
            
            # Show summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                # Count only valid components (exclude "No Component")
                valid_components_count = len([item for item in components_data if item['Component'] != 'No Component'])
                st.metric("Components with Issues", valid_components_count)
            with col2:
                total_story_task = sum(item['# Story/Task'] for item in components_data)
                st.metric("Total Story/Task", total_story_task)
            with col3:
                total_bugs = sum(item['# Bugs'] for item in components_data)
                st.metric("Total Bugs", total_bugs)
        
        else:
            st.info("No component issues found in the current sprint.")
    
    st.divider()
    
    # Display Release Information
    st.subheader("🚀 Releases & Fix Versions")
    
    with st.spinner("Fetching release information..."):
        released_versions, upcoming_versions = get_release_versions(jira, jira_config['project_key'])
    
    # Display in two columns - Released and Upcoming
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 📦 Last 5 Released Versions:")
        if released_versions:
            for version in released_versions:
                with st.container(border=True):
                    st.markdown("")  # Add padding
                    # Make title clickable
                    version_url = f"{jira_config['url']}/projects/{jira_config['project_key']}/versions/{version['version_id']}/tab/release-report-all-issues"
                    st.markdown(f"[**{version['name']}**]({version_url})", unsafe_allow_html=True)
                    if version['release_date'] != 'Not set':
                        st.markdown(f"<p style='color: #388e3c; font-size: 16px; font-weight: bold; margin: 5px 0;'>📅 {version['release_date']}</p>", unsafe_allow_html=True)
                    st.text(version['description'][:150] + ("..." if len(version['description']) > 150 else ""))
        else:
            st.info("No released versions found.")
    
    with col2:
        st.markdown("##### 🎯 Next 5 Upcoming Versions:")
        if upcoming_versions:
            for version in upcoming_versions:
                with st.container(border=True):
                    st.markdown("")  # Add padding
                    # Make title clickable
                    version_url = f"{jira_config['url']}/projects/{jira_config['project_key']}/versions/{version['version_id']}/tab/release-report-all-issues"
                    st.markdown(f"[**{version['name']}**]({version_url})", unsafe_allow_html=True)
                    if version['release_date'] != 'Not set':
                        # Check if release date is in the past
                        is_overdue = is_date_past(version['release_date'])
                        
                        if is_overdue:
                            # Show warning for overdue releases
                            st.markdown(f"<p style='color: #d32f2f; font-size: 16px; font-weight: bold; margin: 5px 0;'>⚠️ OVERDUE - 📅 {version['release_date']}</p>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<p style='color: #4caf50; font-size: 16px; font-weight: bold; margin: 5px 0;'>📅 {version['release_date']}</p>", unsafe_allow_html=True)
                    st.text(version['description'][:150] + ("..." if len(version['description']) > 150 else ""))
        else:
            st.info("No upcoming versions found.")
