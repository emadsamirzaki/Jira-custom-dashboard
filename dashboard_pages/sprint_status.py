"""Sprint Status page showing component details."""

import streamlit as st
import logging

from jira_integration.client import get_jira_connection, validate_jira_connection
from jira_integration.queries import get_active_sprint, get_component_details
from ui.utils import display_refresh_button
from ui.performance import load_data_parallel, display_update_timestamp

logger = logging.getLogger(__name__)


def render_sprint_status_page(jira_config, component_name):
    """Render the sprint status page for a specific component."""
    
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
        return
    
    # Get active sprint info for filtering
    sprint_info = get_active_sprint(jira, jira_config['board_id'])
    sprint_id = sprint_info['id'] if sprint_info else None
    
    # Get component details with spinner
    def fetch_component_details():
        return get_component_details(jira, jira_config['project_key'], component_name, sprint_id)
    
    with st.spinner(f"Loading {component_name} information..."):
        results = load_data_parallel([
            ("Component Details", fetch_component_details)
        ])
    
    # Display timestamp
    display_update_timestamp()
    
    component_details = results.get('Component Details')
    
    if component_details:
        # Display component metrics
        st.subheader("📊 Component Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Issues", component_details['total_count'])
        with col2:
            st.metric("Stories/Tasks", component_details['story_task_count'])
        with col3:
            st.metric("Bugs", component_details['bugs_count'])
        with col4:
            if sprint_info:
                st.metric("Sprint", sprint_info['name'])
        
        st.divider()
        
        # Display status breakdown
        st.subheader("📈 Status Breakdown")
        
        if component_details['status_breakdown']:
            import pandas as pd
            status_data = [
                {'Status': status, 'Count': count}
                for status, count in component_details['status_breakdown'].items()
            ]
            status_df = pd.DataFrame(status_data).sort_values('Count', ascending=False)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                # Display as table
                st.dataframe(
                    status_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Status": st.column_config.TextColumn("Status", width="medium"),
                        "Count": st.column_config.NumberColumn("Count", format="%d")
                    }
                )
            
            with col2:
                # Display as chart
                st.bar_chart(status_df.set_index('Status'))
    
    else:
        st.error(f"Unable to fetch details for {component_name}")
