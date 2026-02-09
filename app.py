"""
Simple Streamlit application to connect with Jira Cloud.
Displays project information and current sprint details.
"""

import streamlit as st
import yaml
from jira import JIRA
from datetime import datetime, timedelta
import os
import pandas as pd


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Jira Dashboard",
    page_icon="📊",
    layout="wide"
)


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================
def load_config():
    """Load Jira configuration from config.yaml file."""
    config_path = "config.yaml"
    
    if not os.path.exists(config_path):
        st.error(f"Configuration file not found: {config_path}")
        st.stop()
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        st.error(f"Error loading configuration: {str(e)}")
        st.stop()


# ============================================================================
# JIRA CONNECTION
# ============================================================================
@st.cache_resource
def get_jira_connection(url, email, api_token):
    """
    Establish and cache connection to Jira Cloud.
    Using st.cache_resource to maintain single connection throughout session.
    """
    try:
        jira = JIRA(
            server=url,
            basic_auth=(email, api_token)
        )
        return jira
    except Exception as e:
        return None


def validate_jira_connection(jira):
    """Test Jira connection and return validation result."""
    try:
        if jira is None:
            return False, "Failed to establish Jira connection"
        
        # Try to get current user to validate connection
        jira.current_user()
        return True, "Connected to Jira successfully"
    
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


# ============================================================================
# JIRA DATA RETRIEVAL
# ============================================================================
def get_project_info(jira, project_key):
    """
    Retrieve project information from Jira.
    """
    try:
        project = jira.project(project_key)
        return {
            'name': project.name,
            'key': project.key,
            'description': project.description if hasattr(project, 'description') else 'No description'
        }
    except Exception as e:
        return None


def get_active_sprint(jira, board_id):
    """
    Retrieve the active/current sprint information from Jira board.
    """
    try:
        # Get sprints from the board
        sprints = jira.sprints(board_id=board_id, state='active')
        
        if not sprints:
            return None
        
        # Get the first (current) active sprint
        sprint = sprints[0]
        
        return {
            'name': sprint.name,
            'id': sprint.id,
            'start_date': sprint.startDate if hasattr(sprint, 'startDate') else 'Not set',
            'end_date': sprint.endDate if hasattr(sprint, 'endDate') else 'Not set',
            'state': sprint.state if hasattr(sprint, 'state') else 'Unknown'
        }
    except Exception as e:
        return None


def get_components_issues_count(jira, project_key, sprint_id=None):
    """
    Retrieve component information and count issues by type (Story/Task vs Bugs).
    If sprint_id is provided, only count issues in that sprint.
    Includes a row for issues with no component assigned.
    Returns a list of dictionaries with component data.
    """
    try:
        import pandas as pd
        
        # Get all components in the project
        project = jira.project(project_key)
        components = project.components
        
        # Build list to store component data
        components_data = []
        
        # Process regular components
        if components:
            for component in components:
                component_name = component.name
                component_id = component.id
                
                # Build JQL query with sprint filter if provided
                sprint_filter = f' AND sprint = {sprint_id}' if sprint_id else ''
                
                # Query issues with this component
                # Count Story and Task types
                jql_story_task = f'project = {project_key} AND component = {component_id} AND type in (Story, Task){sprint_filter}'
                story_task_count = jira.search_issues(jql_story_task, maxResults=0).total
                
                # Count Bug type
                jql_bugs = f'project = {project_key} AND component = {component_id} AND type = Bug{sprint_filter}'
                bugs_count = jira.search_issues(jql_bugs, maxResults=0).total
                
                # Calculate total
                total_count = story_task_count + bugs_count
                
                # Only add component if it has issues
                if total_count > 0:
                    components_data.append({
                        'Component': component_name,
                        '# Story/Task': story_task_count,
                        '# Bugs': bugs_count,
                        'Total': total_count
                    })
        
        # Add row for issues with no component assigned
        sprint_filter = f' AND sprint = {sprint_id}' if sprint_id else ''
        
        # Query issues WITHOUT component
        jql_story_task_no_comp = f'project = {project_key} AND component is EMPTY AND type in (Story, Task){sprint_filter}'
        story_task_no_comp = jira.search_issues(jql_story_task_no_comp, maxResults=0).total
        
        jql_bugs_no_comp = f'project = {project_key} AND component is EMPTY AND type = Bug{sprint_filter}'
        bugs_no_comp = jira.search_issues(jql_bugs_no_comp, maxResults=0).total
        
        total_no_comp = story_task_no_comp + bugs_no_comp
        
        # Add "No Component" row
        if total_no_comp > 0:
            components_data.append({
                'Component': 'No Component',
                '# Story/Task': story_task_no_comp,
                '# Bugs': bugs_no_comp,
                'Total': total_no_comp
            })
        
        # Sort by Total descending
        components_data.sort(key=lambda x: x['Total'], reverse=True)
        
        return components_data if components_data else None
    
    except Exception as e:
        return None


def get_project_components(jira, project_key, preferred_order=None):
    """
    Retrieve all components in a project.
    Optionally sort by preferred order.
    Returns a list of component names.
    """
    try:
        project = jira.project(project_key)
        components = project.components
        
        if components:
            component_names = [component.name for component in components]
            
            # If preferred order is provided, sort accordingly
            if preferred_order:
                # Create a sorted list based on preferred order
                sorted_components = []
                remaining_components = set(component_names)
                
                # Add components in preferred order
                for preferred in preferred_order:
                    for comp in component_names:
                        if preferred.lower() in comp.lower():
                            sorted_components.append(comp)
                            remaining_components.discard(comp)
                            break
                
                # Add any remaining components at the end
                sorted_components.extend(sorted(remaining_components))
                
                return sorted_components
            
            return component_names
        return []
    
    except Exception as e:
        return []


# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================
with st.sidebar:
    st.header("📊 Navigation")
    
    # Navigation menu with session state management
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Home'
    
    if 'selected_component' not in st.session_state:
        st.session_state.selected_component = None
    
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
        
        except:
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
        
        except:
            st.session_state.current_page = 'Home'
    
    else:
        st.session_state.current_page = selected_main
        st.session_state.selected_component = None
    
    st.divider()
    st.subheader("About")
    st.info("Simple Jira Cloud dashboard for tracking project and sprint information.")


def get_component_details(jira, project_key, component_name, sprint_id=None):
    """
    Get detailed information about a specific component and its issues.
    """
    try:
        project = jira.project(project_key)
        component = None
        
        # Find the component by name
        for comp in project.components:
            if comp.name == component_name:
                component = comp
                break
        
        if not component:
            return None
        
        # Build JQL query
        sprint_filter = f' AND sprint = {sprint_id}' if sprint_id else ''
        
        # Get all issues for this component
        jql = f'project = {project_key} AND component = {component.id}{sprint_filter} ORDER BY updated DESC'
        issues = jira.search_issues(jql, maxResults=50)
        
        # Get issue type breakdown
        jql_story_task = f'project = {project_key} AND component = {component.id} AND type in (Story, Task){sprint_filter}'
        story_task_count = jira.search_issues(jql_story_task, maxResults=0).total
        
        jql_bugs = f'project = {project_key} AND component = {component.id} AND type = Bug{sprint_filter}'
        bugs_count = jira.search_issues(jql_bugs, maxResults=0).total
        
        # Get status breakdown
        status_breakdown = {}
        for issue in issues:
            status = issue.fields.status.name
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        return {
            'name': component_name,
            'story_task_count': story_task_count,
            'bugs_count': bugs_count,
            'total_count': story_task_count + bugs_count,
            'status_breakdown': status_breakdown,
            'recent_issues': issues
        }
    
    except Exception as e:
        return None


def get_component_capability_status(jira, project_key, component_name, sprint_id=None):
    """
    Get comprehensive capability status for a component including open ticket counts
    across different priority levels, sprint status, and time-based metrics.
    
    Returns a dictionary with counts organized by issue type (Bugs/Features) and filters.
    """
    try:
        project = jira.project(project_key)
        component = None
        
        # Find the component by name
        for comp in project.components:
            if comp.name == component_name:
                component = comp
                break
        
        if not component:
            return None
        
        # Initialize counters
        data = {
            'Defects': {},
            'Features': {}
        }
        
        # Base component filter
        component_filter = f'AND component = {component.id}'
        
        # Time-based filters
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Define all the criteria we need to count
        # Using proper JQL syntax with IN operator for multiple values
        criteria = [
            # Backlog columns (NOT in current sprint)
            ('Backlog Critical', f'{component_filter} AND resolution = Unresolved AND priority IN (Highest, Critical) AND sprint != {sprint_id}'),
            ('Backlog High', f'{component_filter} AND resolution = Unresolved AND priority = High AND sprint != {sprint_id}'),
            ('Backlog Medium', f'{component_filter} AND resolution = Unresolved AND priority = Medium AND sprint != {sprint_id}'),
            ('Backlog Low', f'{component_filter} AND resolution = Unresolved AND priority = Low AND sprint != {sprint_id}'),
            # Sprint columns (IN current sprint)
            ('Sprint Critical', f'{component_filter} AND resolution = Unresolved AND priority IN (Highest, Critical) AND sprint = {sprint_id}'),
            ('Sprint High', f'{component_filter} AND resolution = Unresolved AND priority = High AND sprint = {sprint_id}'),
            ('Sprint Medium', f'{component_filter} AND resolution = Unresolved AND priority = Medium AND sprint = {sprint_id}'),
            ('Sprint Low', f'{component_filter} AND resolution = Unresolved AND priority = Low AND sprint = {sprint_id}'),
            # Other metrics
            ('Total', f'{component_filter} AND resolution = Unresolved'),
            ('Resolved in last 30 days', f'{component_filter} AND resolved >= {thirty_days_ago}'),
            ('Added in last 30 days', f'{component_filter} AND created >= {thirty_days_ago}'),
        ]
        
        # Count issues for each criteria and issue type
        for column_name, base_jql in criteria:
            # Count Defects (Bugs)
            jql_defect = f'project = {project_key} {base_jql} AND type = Bug'
            defect_count = jira.search_issues(jql_defect, maxResults=0).total
            data['Defects'][column_name] = defect_count
            
            # Count Features (Story/Task)
            jql_feature = f'project = {project_key} {base_jql} AND type IN (Story, Task)'
            feature_count = jira.search_issues(jql_feature, maxResults=0).total
            data['Features'][column_name] = feature_count
        
        return data
    
    except Exception as e:
        st.error(f"Error fetching capability status: {str(e)}")
        return None


# ============================================================================
# PAGE HANDLERS
# ============================================================================
def main():
    """Main application logic."""
    
    # Load configuration
    config = load_config()
    jira_config = config.get('jira', {})
    
    # Validate configuration completeness
    required_fields = ['url', 'email', 'api_token', 'project_key', 'board_id']
    missing_fields = [f for f in required_fields if not jira_config.get(f) or jira_config.get(f) in ['your-domain.atlassian.net', 'your-email@example.com', 'your-api-token-here', 'MYPROJECT']]
    
    if missing_fields:
        st.error(f"""
        ❌ Configuration incomplete. Please update config.yaml with your Jira details:
        
        Missing or placeholder values: {', '.join(missing_fields)}
        
        See README.md for instructions on how to find these values.
        """)
        st.stop()
    
    # ========================================================================
    # HOME PAGE
    # ========================================================================
    if st.session_state.current_page == 'Home':
        st.title("🏠 Home - Jira Dashboard")
        
        # Manual refresh button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
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
                    height=100,
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
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Sprint Name", sprint_info['name'])
            
            
            with col3:
                start_date = sprint_info['start_date']
                if isinstance(start_date, str) and start_date != 'Not set':
                    # Parse and format date
                    try:
                        date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        start_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        pass
                st.metric("Sprint Start Date", start_date)
            
            with col4:
                end_date = sprint_info['end_date']
                if isinstance(end_date, str) and end_date != 'Not set':
                    # Parse and format date
                    try:
                        date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        end_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        pass
                st.metric("Sprint End Date", end_date)
            
            st.divider()
            st.info(f"Sprint State: **{sprint_info['state']}**")
        
        else:
            st.warning("No active sprint found. Create a sprint in Jira or check the board ID in config.yaml")
        
        st.divider()
        
        # Display Components and Issues Count (Current Sprint)
        st.subheader("📦 Issues by Component (Current Sprint)")
        
        with st.spinner("Fetching component issues..."):
            components_data = get_components_issues_count(jira, jira_config['project_key'], sprint_info['id'])
        
        if components_data:
            # Create columns for better formatting
            import pandas as pd
            
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
                st.metric("Components with Issues", len(components_data))
            with col2:
                total_story_task = sum(item['# Story/Task'] for item in components_data)
                st.metric("Total Story/Task", total_story_task)
            with col3:
                total_bugs = sum(item['# Bugs'] for item in components_data)
                st.metric("Total Bugs", total_bugs)
        
        else:
            st.info("No component issues found in the current sprint.")
    
    # ========================================================================
    # SPRINT STATUS - COMPONENT STATUS PAGE
    # ========================================================================
    elif st.session_state.current_page.startswith('Sprint Status - '):
        component_name = st.session_state.selected_component
        
        st.title(f"📅 {component_name} - Weekly Status")
        
        # Manual refresh button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
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
        
        # Get component details
        with st.spinner(f"Fetching {component_name} information..."):
            component_details = get_component_details(jira, jira_config['project_key'], component_name, sprint_id)
        
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
    
    # ========================================================================
    # COMPONENT CAPABILITY STATUS PAGE
    # ========================================================================
    elif st.session_state.current_page.startswith('Component Capability Status - '):
        component_name = st.session_state.selected_component
        
        st.title(f"🎯 {component_name} - Component Capability Status")
        
        # Manual refresh button
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        with col3:
            last_updated = datetime.now().strftime("%H:%M:%S")
            st.caption(f"Updated: {last_updated}")
        
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
        
        # Get active sprint info
        sprint_info = get_active_sprint(jira, jira_config['board_id'])
        sprint_id = sprint_info['id'] if sprint_info else None
        
        if not sprint_id:
            st.warning("⚠️ No active sprint found. Please create a sprint in Jira.")
            return
        
        # Display subsection title
        st.subheader("📊 Counts of Open Tickets")
        
        # Get capability status data
        with st.spinner(f"Fetching {component_name} capability status..."):
            capability_data = get_component_capability_status(jira, jira_config['project_key'], component_name, sprint_id)
        
        if capability_data:
            # Prepare data for display
            table_data = []
            
            # Process Defects (Bugs)
            defect_row = {'Issue Type': 'Defects'}
            defect_row.update(capability_data['Defects'])
            table_data.append(defect_row)
            
            # Process Features (Tasks/Stories)
            feature_row = {'Issue Type': 'Features'}
            feature_row.update(capability_data['Features'])
            table_data.append(feature_row)
            
            # Create DataFrame
            df = pd.DataFrame(table_data)
            
            # Define column order
            column_order = [
                'Issue Type',
                'Backlog Critical',
                'Backlog High',
                'Backlog Medium',
                'Backlog Low',
                'Sprint Critical',
                'Sprint High',
                'Sprint Medium',
                'Sprint Low',
                'Total',
                'Resolved in last 30 days',
                'Added in last 30 days'
            ]
            
            # Reorder columns
            df = df[[col for col in column_order if col in df.columns]]
            
            # Display table with column configuration
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Issue Type': st.column_config.TextColumn('Issue Type', width='medium'),
                    'Backlog Critical': st.column_config.NumberColumn('Backlog Critical', format='%d'),
                    'Backlog High': st.column_config.NumberColumn('Backlog High', format='%d'),
                    'Backlog Medium': st.column_config.NumberColumn('Backlog Medium', format='%d'),
                    'Backlog Low': st.column_config.NumberColumn('Backlog Low', format='%d'),
                    'Sprint Critical': st.column_config.NumberColumn('Sprint Critical', format='%d'),
                    'Sprint High': st.column_config.NumberColumn('Sprint High', format='%d'),
                    'Sprint Medium': st.column_config.NumberColumn('Sprint Medium', format='%d'),
                    'Sprint Low': st.column_config.NumberColumn('Sprint Low', format='%d'),
                    'Total': st.column_config.NumberColumn('Total', format='%d'),
                    'Resolved in last 30 days': st.column_config.NumberColumn('Resolved in last 30 days', format='%d'),
                    'Added in last 30 days': st.column_config.NumberColumn('Added in last 30 days', format='%d'),
                }
            )
            
            st.divider()
            
            # Display summary information
            st.subheader("📈 Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_defects = capability_data['Defects'].get('Total', 0)
                st.metric("Total Defects", total_defects)
            
            with col2:
                total_features = capability_data['Features'].get('Total', 0)
                st.metric("Total Features", total_features)
            
            with col3:
                critical_issues = (capability_data['Defects'].get('Sprint Critical', 0) + 
                                 capability_data['Features'].get('Sprint Critical', 0))
                st.metric("Sprint Critical Issues", critical_issues)
            
            with col4:
                high_issues = (capability_data['Defects'].get('Sprint High', 0) + 
                             capability_data['Features'].get('Sprint High', 0))
                st.metric("Sprint High Issues", high_issues)
        
        else:
            st.error(f"Unable to fetch capability status for {component_name}")
    
    # ========================================================================
    # SPRINT METRICS (Placeholder)
    # ========================================================================
    elif st.session_state.current_page == 'Sprint Metrics':
        st.title("📈 Sprint Metrics")
        st.info("This is a placeholder page. Feature coming soon!")
        st.write("This page will display:")
        st.write("- Velocity trends")
        st.write("- Burndown charts")
        st.write("- Story points vs issues")
        st.write("- Team performance")
    
    # ========================================================================
    # CUSTOM REPORTS (Placeholder)
    # ========================================================================
    elif st.session_state.current_page == 'Custom Reports':
        st.title("📊 Custom Reports")
        st.info("This is a placeholder page. Feature coming soon!")
        st.write("This page will display:")
        st.write("- Custom JQL queries")
        st.write("- Exportable reports")
        st.write("- Issue breakdowns")
        st.write("- Team metrics")


# ============================================================================
# RUN APPLICATION
# ============================================================================
if __name__ == "__main__":
    main()
