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
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()


# ============================================================================
# LOGGING UTILITY
# ============================================================================
import logging

# Configure logging based on environment
log_level = os.getenv('LOG_LEVEL', 'WARNING')
logging.basicConfig(
    level=getattr(logging, log_level, logging.WARNING),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS & SETTINGS
# ============================================================================
CACHE_TTL = int(os.getenv('CACHE_TTL', 300))  # Default 5 minutes, configurable
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))  # API request timeout in seconds
MAX_RETRIES = 3  # Number of retries for failed requests





# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Jira Dashboard | Wolters Kluwer",
    page_icon="📊",
    layout="wide"
)


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================
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



# ============================================================================
# JIRA CONNECTION
# ============================================================================
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


def get_release_versions(jira, project_key):
    """
    Retrieve released and upcoming versions (fix versions) from the project.
    Returns two lists: released_versions and upcoming_versions
    Each version contains: name, description, release_date, status, version_id
    For upcoming versions, only includes unreleased and non-archived versions with release dates.
    """
    try:
        project = jira.project(project_key)
        versions = project.versions
        
        released_versions = []
        upcoming_versions = []
        
        for version in versions:
            release_date = version.releaseDate if hasattr(version, 'releaseDate') and version.releaseDate else 'Not set'
            version_id = version.id if hasattr(version, 'id') else None
            
            version_info = {
                'name': version.name,
                'description': version.description if hasattr(version, 'description') and version.description else 'No description',
                'release_date': release_date,
                'status': 'Released' if version.released else 'Unreleased',
                'archived': version.archived if hasattr(version, 'archived') else False,
                'version_id': version_id
            }
            
            if version.released:
                # Only include if has release date
                if release_date != 'Not set':
                    released_versions.append(version_info)
            else:
                # For upcoming: only include unreleased, non-archived versions with release dates
                is_archived = version.archived if hasattr(version, 'archived') else False
                if not is_archived and release_date != 'Not set':
                    upcoming_versions.append(version_info)
        
        # Sort released versions by date (newest first)
        released_versions.sort(
            key=lambda x: x['release_date'],
            reverse=True
        )
        
        # Sort upcoming versions by date (soonest first - ascending)
        upcoming_versions.sort(
            key=lambda x: x['release_date'],
            reverse=False
        )
        
        return released_versions[:5], upcoming_versions[:5]  # Return top 5 each
    
    except Exception as e:
        print(f"Error fetching release versions: {str(e)}")
        return [], []


# ============================================================================
# BRANDING FUNCTIONS
# ============================================================================
def display_branded_header(page_title=""):
    """
    Display the branded header with page title and team name.
    """
    try:
        header_html = f"""
        <style>
        .wk-header {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background: linear-gradient(135deg, #3c70a3 0%, #004d99 100%);
            border-bottom: 3px solid #FF6600;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .wk-page-title {{
            font-size: 28px;
            color: white;
            font-weight: 700;
            margin: 0 0 8px 0;
            letter-spacing: 0.3px;
        }}
        .wk-page-team {{
            font-size: 13px;
            color: #FFB84D;
            font-style: italic;
            margin: 0;
            font-weight: 500;
        }}
        </style>
        
        <div class="wk-header">
            <div class="wk-page-title">{page_title}</div>
            <div class="wk-page-team">InfraOps Engineering Team</div>
        </div>
        """
        
        st.markdown(header_html, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error displaying branded header: {str(e)}")
        st.write("📊 Jira Dashboard")


def display_branded_footer():
    """
    Display the branded footer with team name and copyright information.
    """
    try:
        footer_css = """
        <style>
        .wk-footer {
            margin-top: 40px;
            padding: 20px;
            background: linear-gradient(135deg, #3c70a3 0%, #004d99 100%);
            border-top: 3px solid #FF6600;
            border-radius: 5px;
            text-align: center;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
        }
        .wk-footer-content {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        .wk-footer-text {
            color: white;
            font-size: 12px;
            margin: 0;
        }
        .wk-footer-divider {
            color: #FF6600;
            font-size: 12px;
        }
        .wk-footer-team {
            color: #FF6600;
            font-weight: bold;
            font-size: 13px;
        }
        </style>
        
        <div class="wk-footer">
            <div class="wk-footer-content">
                <span class="wk-footer-text">©2026 Wolters Kluwer</span>
                <span class="wk-footer-divider">|</span>
                <span class="wk-footer-team">InfraOps Engineering Team</span>
                <span class="wk-footer-divider">|</span>
                <span class="wk-footer-text">Jira Cloud Dashboard</span>
            </div>
        </div>
        """
        
        st.markdown(footer_css, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error displaying branded footer: {str(e)}")


# ============================================================================
# SIDEBAR BRANDING
# ============================================================================
def display_sidebar_branding():
    """
    Display Wolters Kluwer branding in the sidebar with logo and company name.
    """
    try:
        import base64
        import os
        
        # Load logo from assets folder
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "wk-logo.png")
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as logo_file:
                logo_data = base64.b64encode(logo_file.read()).decode()
            
            sidebar_html = f"""
            <style>
            .wk-sidebar-brand {{
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 10px;
                padding: 20px 15px;
                background: linear-gradient(135deg, #3c70a3 0%, #004d99 100%);
                border-radius: 8px;
                margin-bottom: 20px;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            }}
            .wk-sidebar-logo {{
                height: 60px;
                object-fit: contain;
            }}
            .wk-sidebar-company {{
                font-size: 16px;
                font-weight: bold;
                color: white;
                letter-spacing: 0.5px;
                margin: 0;
            }}
            .wk-sidebar-team {{
                font-size: 11px;
                color: #e0e0e0;
                font-style: italic;
                margin: 0;
            }}
            </style>
            
            <div class="wk-sidebar-brand">
                <img src="data:image/png;base64,{logo_data}" alt="Wolters Kluwer" class="wk-sidebar-logo"/>
                <p class="wk-sidebar-company">WOLTERS KLUWER</p>
                <p class="wk-sidebar-team">InfraOps Engineering Team</p>
            </div>
            """
            st.markdown(sidebar_html, unsafe_allow_html=True)
        else:
            # Fallback if logo not found
            st.write("**WOLTERS KLUWER**")
            st.write("InfraOps Engineering Team")
    except Exception as e:
        logger.error(f"Error displaying sidebar branding: {str(e)}")
        st.write("**WOLTERS KLUWER**")


# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================
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
            # Backlog columns (NOT in current sprint, including items with no sprint)
            ('Backlog Critical', f'{component_filter} AND resolution = Unresolved AND priority IN (Highest, Critical) AND (sprint != {sprint_id} OR sprint is EMPTY)'),
            ('Backlog High', f'{component_filter} AND resolution = Unresolved AND priority = High AND (sprint != {sprint_id} OR sprint is EMPTY)'),
            ('Backlog Medium', f'{component_filter} AND resolution = Unresolved AND priority = Medium AND (sprint != {sprint_id} OR sprint is EMPTY)'),
            ('Backlog Low', f'{component_filter} AND resolution = Unresolved AND priority IN (Low, Lowest) AND (sprint != {sprint_id} OR sprint is EMPTY)'),
            # Sprint columns (IN current sprint)
            ('Sprint Critical', f'{component_filter} AND resolution = Unresolved AND priority IN (Highest, Critical) AND sprint = {sprint_id}'),
            ('Sprint High', f'{component_filter} AND resolution = Unresolved AND priority = High AND sprint = {sprint_id}'),
            ('Sprint Medium', f'{component_filter} AND resolution = Unresolved AND priority = Medium AND sprint = {sprint_id}'),
            ('Sprint Low', f'{component_filter} AND resolution = Unresolved AND priority IN (Low, Lowest) AND sprint = {sprint_id}'),
            # Other metrics
            ('Total', f'{component_filter} AND resolution = Unresolved'),
            ('Resolved in last 30 days', f'{component_filter} AND resolved >= {thirty_days_ago} AND status != Cancelled'),
            ('Added in last 30 days', f'{component_filter} AND created >= {thirty_days_ago}'),
        ]
        
        # Count issues for each criteria and issue type
        for column_name, base_jql in criteria:
            # Count Defects (Bugs only)
            jql_defect = f'project = {project_key} {base_jql} AND type = Bug'
            defect_count = jira.search_issues(jql_defect, maxResults=0).total
            data['Defects'][column_name] = defect_count
            
            # Count Features (Story or Task only)
            jql_feature = f'project = {project_key} {base_jql} AND (type = Story OR type = Task)'
            feature_count = jira.search_issues(jql_feature, maxResults=0).total
            data['Features'][column_name] = feature_count
        
        return data
    
    except Exception as e:
        st.error(f"Error fetching capability status: {str(e)}")
        return None


def get_component_capability_status_historical(jira, project_key, component_name, sprint_id=None, days_ago=7):
    """
    Get capability status for issues as they existed N days ago.
    Used for week-over-week comparisons.
    
    Returns a dictionary with counts for comparison.
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
            logger.debug(f"Component '{component_name}' not found in project {project_key}")
            return None
        
        logger.debug(f"Found component '{component_name}' with ID {component.id}")
        
        # Initialize counters
        data = {
            'Defects': {},
            'Features': {}
        }
        
        # Base component filter
        component_filter = f'AND component = {component.id}'
        
        # Date range for historical data
        date_n_days_ago = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        # For "Added in last 30 days" as of N days ago, we need (N+30) days ago
        date_past_30_days_ago = (datetime.now() - timedelta(days=days_ago+30)).strftime('%Y-%m-%d')
        
        logger.debug(f"Date range - {days_ago} days ago: {date_n_days_ago}, 30+{days_ago} days ago: {date_past_30_days_ago}")
        
        # For historical comparison, get issues created before N days ago (which existed then)
        criteria = [
            ('Total', f'{component_filter} AND resolution = Unresolved AND created < "{date_n_days_ago}"'),
            ('Added in last 30 days', f'{component_filter} AND created >= "{date_past_30_days_ago}" AND created < "{date_n_days_ago}"'),
            ('Resolved in last 30 days', f'{component_filter} AND resolved >= "{date_past_30_days_ago}" AND status != "Cancelled" AND resolved < "{date_n_days_ago}"'),
        ]
        
        # Count issues for each criteria and issue type
        for column_name, base_jql in criteria:
            # Count Defects (Bugs only)
            jql_defect = f'project = {project_key} {base_jql} AND type = Bug'
            defect_count = jira.search_issues(jql_defect, maxResults=0).total
            data['Defects'][column_name] = defect_count
            logger.debug(f"{column_name} - Defects: {defect_count}")
            
            # Count Features (Story or Task only)
            jql_feature = f'project = {project_key} {base_jql} AND (type = Story OR type = Task)'
            feature_count = jira.search_issues(jql_feature, maxResults=0).total
            data['Features'][column_name] = feature_count
            logger.debug(f"{column_name} - Features: {feature_count}")
        
        logger.debug(f"Historical data = {data}")
        return data
    
    except Exception as e:
        st.error(f"Error fetching historical capability status: {str(e)}")
        return None


def get_critical_high_issues(jira, project_key, component_name, sprint_id=None, sprint_only=False):
    """
    Get detailed information about Critical and High priority issues.
    
    Args:
        jira: Jira connection
        project_key: Project key
        component_name: Component name to filter by
        sprint_id: Current sprint ID
        sprint_only: If True, get only sprint issues; if False, get backlog issues
    
    Returns:
        List of issues with details
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
        
        # Build JQL based on sprint_only flag
        component_filter = f'AND component = {component.id}'
        base_query = f'project = {project_key} {component_filter} AND resolution = Unresolved AND priority IN (Highest, Critical, High) AND type IN (Story, Task, Bug)'
        
        if sprint_only:
            # Sprint issues only
            jql = f'{base_query} AND sprint = {sprint_id} ORDER BY priority DESC, created DESC'
        else:
            # Backlog issues (not in current sprint and no sprint)
            jql = f'{base_query} AND (sprint != {sprint_id} OR sprint is EMPTY) ORDER BY priority DESC, created DESC'
        
        # Get issues without fields restriction to get all available fields including sprint
        # Then fetch each issue individually to ensure all fields are populated
        initial_issues = jira.search_issues(jql, maxResults=100, expand='changelog')
        
        if not initial_issues:
            return None
        
        # Re-fetch each issue to ensure all fields including sprint are available
        full_issues = []
        for issue in initial_issues:
            try:
                # Fetch the issue with all available data
                full_issue = jira.issue(issue.key, expand='changelog')
                full_issues.append(full_issue)
            except Exception as e:
                logger.debug(f"Error fetching full issue {issue.key}: {str(e)}")
                # Fallback to the initial issue if re-fetch fails
                full_issues.append(issue)
        
        return full_issues if full_issues else None
    
    except Exception as e:
        st.error(f"Error fetching critical/high issues: {str(e)}")
        return None


def get_target_completion_date(issue, jira=None, base_url=None, debug=False):
    """
    Get the target completion date for an issue.
    Priority:
    1. If due_date exists, return it
    2. If no due_date, try to get sprint end date (if issue is assigned to a sprint)
    3. If not assigned to any sprint, return "N/A"
    
    Args:
        issue: Jira issue object
        jira: Jira connection (optional, needed for REST API calls)
        base_url: Jira server URL (needed for REST API calls)
        debug: If True, also returns debug info as tuple (result, debug_info)
    
    Returns:
        String with display text and optional hint
        If debug=True: tuple of (result_string, {debug_info})
    """
    debug_info = {}
    try:
        # Check if due_date exists
        if issue.fields.duedate:
            debug_info['due_date_found'] = issue.fields.duedate
            if debug:
                return issue.fields.duedate, debug_info
            return issue.fields.duedate
        
        debug_info['due_date_found'] = False
        
        # Try to get sprint information via REST API if jira connection provided
        sprint_end_date = None
        sprint_source = None
        
        if jira and base_url:
            try:
                # Use REST API to get all fields including sprint data
                base_url = base_url.rstrip('/')
                response = jira._session.get(f"{base_url}/rest/api/3/issue/{issue.key}")
                if response.status_code == 200:
                    issue_data = response.json()
                    fields_data = issue_data.get('fields', {})
                    debug_info['rest_api_fields_checked'] = True
                    
                    # Check customfield_10020 which contains sprint data for this Jira instance
                    sprint_field = fields_data.get('customfield_10020')
                    if sprint_field:
                        debug_info['sprint_from_rest_api'] = f'customfield_10020: {str(sprint_field)[:150]}'
                        
                        # Sprint field should be a list of sprint objects
                        if isinstance(sprint_field, list) and len(sprint_field) > 0:
                            sprint_data = sprint_field[0]  # Get the first (active) sprint
                            if isinstance(sprint_data, dict) and 'endDate' in sprint_data:
                                sprint_end_date = sprint_data['endDate']
                                sprint_source = 'customfield_10020.endDate (REST API)'
            except Exception as e:
                debug_info['rest_api_error'] = str(e)
        
        # Fallback: Try direct sprint field if it exists
        if not sprint_end_date:
            sprint_related = [f for f in dir(issue.fields) if 'sprint' in f.lower()]
            debug_info['sprint_related_fields'] = sprint_related
            
            if hasattr(issue.fields, 'sprint') and issue.fields.sprint:
                sprint_data = issue.fields.sprint
                debug_info['sprint_field_exists'] = True
                debug_info['sprint_field_type'] = str(type(sprint_data))
                debug_info['sprint_field_value'] = str(sprint_data)[:200]
                
                # Sprint data might be a list
                if isinstance(sprint_data, list) and len(sprint_data) > 0:
                    sprint_data = sprint_data[0]
                
                # Try extracting endDate from sprint object or dict
                if hasattr(sprint_data, 'endDate'):
                    sprint_end_date = getattr(sprint_data, 'endDate', None)
                    sprint_source = 'sprint.endDate (object)'
                elif isinstance(sprint_data, dict) and 'endDate' in sprint_data:
                    sprint_end_date = sprint_data.get('endDate')
                    sprint_source = 'sprint.endDate (dict)'
                elif isinstance(sprint_data, str):
                    # Sprint might be a string representation, try to parse it
                    import re
                    match = re.search(r'endDate=([^,\]]+)', str(sprint_data))
                    if match:
                        sprint_end_date = match.group(1)
                        sprint_source = 'sprint.endDate (regex parse)'
            else:
                debug_info['sprint_field_exists'] = False
        
        # If not found, try common custom field IDs for sprint
        if not sprint_end_date:
            sprint_field_ids = ['customfield_10010', 'customfield_10001', 'customfield_10006', 'customfield_10007']
            
            for field_id in sprint_field_ids:
                if hasattr(issue.fields, field_id):
                    sprint_data = getattr(issue.fields, field_id, None)
                    if sprint_data:
                        debug_info[f'{field_id}_found'] = True
                        debug_info[f'{field_id}_type'] = str(type(sprint_data))
                        debug_info[f'{field_id}_value'] = str(sprint_data)[:200]
                        
                        # Sprint data might be a list or a single object
                        if isinstance(sprint_data, list) and len(sprint_data) > 0:
                            sprint_data = sprint_data[0]
                        
                        # Try extracting endDate
                        try:
                            if hasattr(sprint_data, 'endDate'):
                                sprint_end_date = getattr(sprint_data, 'endDate', None)
                                sprint_source = f'{field_id}.endDate (object)'
                        except (AttributeError, TypeError):
                            pass
                        
                        # Try as dictionary
                        if not sprint_end_date and isinstance(sprint_data, dict):
                            sprint_end_date = sprint_data.get('endDate', None)
                            if sprint_end_date:
                                sprint_source = f'{field_id}.endDate (dict)'
                        
                        # Try parsing from string
                        if not sprint_end_date and isinstance(sprint_data, str):
                            import re
                            match = re.search(r'endDate=([^,\]]+)', str(sprint_data))
                            if match:
                                sprint_end_date = match.group(1)
                                sprint_source = f'{field_id}.endDate (regex parse)'
                        
                        if sprint_end_date:
                            break
        
        debug_info['sprint_end_date_found'] = sprint_end_date is not None
        debug_info['sprint_source'] = sprint_source
        
        # Format and return the sprint end date if found
        if sprint_end_date:
            try:
                # Clean up the date string
                date_str = str(sprint_end_date).replace('Z', '+00:00').split('T')[0] if 'T' in str(sprint_end_date) else str(sprint_end_date)
                
                # Try parsing as ISO format if it looks like a date
                if len(date_str) >= 10:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')[:10])
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    debug_info['formatted_date'] = formatted_date
                    # Format with styled hint
                    result = f"{formatted_date} <span style='color: #999; font-size: 0.85em; font-style: italic;'>(Sprint Date)</span>"
                    if debug:
                        return result, debug_info
                    return result
                else:
                    result = f"{sprint_end_date} <span style='color: #999; font-size: 0.85em; font-style: italic;'>(Sprint Date)</span>"
                    if debug:
                        return result, debug_info
                    return result
            except Exception as date_format_error:
                logger.debug(f"Error formatting sprint end date '{sprint_end_date}': {str(date_format_error)}")
                debug_info['formatting_error'] = str(date_format_error)
                result = f"{sprint_end_date} <span style='color: #999; font-size: 0.85em; font-style: italic;'>(Sprint Date)</span>"
                if debug:
                    return result, debug_info
                return result
        
        # If no sprint assignment or sprint end date found, return N/A
        if debug:
            return "N/A", debug_info
        return "N/A"
    
    except Exception as e:
        logger.debug(f"Error getting target completion date: {str(e)}")
        debug_info['error'] = str(e)
        if debug:
            return "N/A", debug_info
        return "N/A"


def get_resolution_approach(issue):
    """
    Get the Resolution Approach / Progress Notes field from an issue.
    
    Args:
        issue: Jira issue object
    
    Returns:
        Resolution approach text or 'N/A' if not found or empty
    """
    try:
        # The correct field ID for Resolution approach / Progress notes
        field_id = 'customfield_11249'
        
        if hasattr(issue.fields, field_id):
            value = getattr(issue.fields, field_id)
            if value:  # Only return if value is not None/empty
                # Handle different value types
                if isinstance(value, str):
                    # Clean up whitespace and return
                    cleaned = value.strip()
                    if cleaned:
                        return cleaned[:500]  # Truncate very long text
                elif isinstance(value, dict):
                    # Could be a complex field object
                    if 'value' in value:
                        return str(value['value']).strip()[:500]
                    elif 'name' in value:
                        return str(value['name']).strip()[:500]
                # For other types, convert to string
                val_str = str(value).strip()
                if val_str and val_str.lower() != 'none':
                    return val_str[:500]
        
        # If nothing found or empty, return N/A
        return 'N/A'
    
    except Exception as e:
        logger.debug(f"Error getting resolution approach: {str(e)}")
        return 'N/A'


@st.cache_data(ttl=CACHE_TTL)
def get_flagged_issues(_jira, project_key, component_name):
    """
    Get all issues marked as Flagged in the component.
    
    Args:
        _jira: Jira connection
        project_key: Project key
        component_name: Component name to filter by
    
    Returns:
        List of flagged issues with details
    """
    try:
        project = _jira.project(project_key)
        component = None
        
        # Find the component by name
        for comp in project.components:
            if comp.name == component_name:
                component = comp
                break
        
        if not component:
            return None
        
        # Search for issues with Flagged custom field in Jira Cloud
        # The 'flagged' field in Jira Cloud queries issues with the flag set
        component_filter = f'AND component = {component.id}'
        jql = f'project = {project_key} {component_filter} AND flagged is not empty AND resolution = Unresolved ORDER BY priority DESC, created DESC'
        
        # Expand changelog and comments to get full comment details
        issues = _jira.search_issues(jql, maxResults=100, expand='changelog,comments')
        
        return issues if issues else None
    
    except Exception as e:
        st.error(f"Error fetching flagged issues: {str(e)}")
        return None


def get_flagged_comment(issue):
    """
    Extract the comment linked to the flag from an issue.
    Searches for the comment that has the 'Flagged' property, not just the latest comment.
    
    Args:
        issue: Jira issue object
    
    Returns:
        String with the flagged comment body, or description/latest comment as fallback
    """
    try:
        if issue.fields.comment and issue.fields.comment.comments:
            # First, try to find the comment linked to the flag
            # In Jira Cloud, flagged comments may have properties indicating the flag
            flagged_comment = None
            
            for comment in issue.fields.comment.comments:
                # Check if comment has properties (which may indicate it's linked to the flag)
                if hasattr(comment, 'properties') and comment.properties:
                    for prop in comment.properties:
                        # Look for flag-related properties
                        if hasattr(prop, 'key') and ('flag' in prop.key.lower() or 'agile' in prop.key.lower()):
                            flagged_comment = comment
                            break
                
                # Alternative: Check if comment body contains flag reference
                if flagged_comment is None and hasattr(comment, 'body') and comment.body:
                    if 'flagged' in comment.body.lower():
                        flagged_comment = comment
                
                if flagged_comment:
                    break
            
            # If no flagged comment found via properties, try to find via changelog
            if not flagged_comment and hasattr(issue, 'changelog') and issue.changelog:
                # Find when the flag was added from changelog
                flag_added_time = None
                for history in issue.changelog.histories:
                    for item in history.items:
                        if item.field == 'Flagged' and item.toString and item.toString.strip():
                            flag_added_time = history.created
                            break
                    if flag_added_time:
                        break
                
                # If flag was added, find comment closest to that time
                if flag_added_time:
                    from datetime import datetime as dt
                    flag_time = dt.fromisoformat(flag_added_time.replace('Z', '+00:00'))
                    closest_comment = None
                    smallest_diff = None
                    
                    for comment in issue.fields.comment.comments:
                        comment_time = dt.fromisoformat(comment.created.replace('Z', '+00:00'))
                        time_diff = abs((flag_time - comment_time).total_seconds())
                        
                        # Get comment within 5 minutes of flag creation
                        if time_diff <= 300:  # 5 minutes
                            if smallest_diff is None or time_diff < smallest_diff:
                                smallest_diff = time_diff
                                closest_comment = comment
                    
                    if closest_comment:
                        flagged_comment = closest_comment
            
            # Return flagged comment if found
            if flagged_comment:
                comment_body = flagged_comment.body if hasattr(flagged_comment, 'body') and flagged_comment.body else 'No comment text'
                return comment_body[:150] + ('...' if len(comment_body) > 150 else '')
            
            # Fallback: return the second-to-last comment (which is often the flag comment)
            # since discussions may continue after flagging
            if len(issue.fields.comment.comments) >= 2:
                fallback_comment = issue.fields.comment.comments[-2]
                comment_body = fallback_comment.body if fallback_comment.body else 'No comment text'
                return comment_body[:150] + ('...' if len(comment_body) > 150 else '')
            
            # Final fallback: latest comment
            latest_comment = issue.fields.comment.comments[-1]
            comment_body = latest_comment.body if latest_comment.body else 'No comment text'
            return comment_body[:150] + ('...' if len(comment_body) > 150 else '')
        
        # Fallback to issue description if no comments
        elif issue.fields.description:
            desc = issue.fields.description
            return desc[:150] + ('...' if len(desc) > 150 else '')
        
        return 'No comment'
    
    except Exception as e:
        return 'Error retrieving comment'


def display_refresh_button():
    """
    Display a consistent refresh button with last updated timestamp across all pages.
    Returns True if refresh was clicked, False otherwise.
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.caption(f"Last Updated: {st.session_state.last_updated_time}")
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.last_updated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()
            return True
    
    return False


def is_date_past(date_string):
    """
    Check if a date string is in the past.
    
    Args:
        date_string: Date string in format 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS.000+0000'
    
    Returns:
        Boolean indicating if date is in the past
    """
    try:
        if date_string == 'Not set':
            return False
        
        # Parse the date string
        if 'T' in date_string:
            # ISO format with time
            release_date = datetime.fromisoformat(date_string.replace('Z', '+00:00')).date()
        else:
            # Simple date format
            release_date = datetime.strptime(date_string, '%Y-%m-%d').date()
        
        today = datetime.now().date()
        return release_date < today
    
    except Exception as e:
        logger.debug(f"Error checking if date is past: {str(e)}")
        return False



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
    # DISPLAY BRANDED HEADER
    # ========================================================================
    # Defensive session state initialization (sidebar also does this, but just in case)
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Home'
    if 'selected_component' not in st.session_state:
        st.session_state.selected_component = None
    
    # Determine page title based on current page
    try:
        base_page_name = st.session_state.current_page.split(' - ')[0]
        selected_component = getattr(st.session_state, 'selected_component', None) or "Select Component"
        
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
    
    # ========================================================================
    # HOME PAGE
    # ========================================================================
    if st.session_state.current_page == 'Home':
        
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

    
    # ========================================================================
    # SPRINT STATUS - COMPONENT STATUS PAGE
    # ========================================================================
    elif st.session_state.current_page.startswith('Sprint Status - '):
        component_name = st.session_state.selected_component
        
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
            import pandas as pd
            
            # Create a styled HTML table with proper grouping
            defect_data = capability_data['Defects']
            feature_data = capability_data['Features']
            
            # Create HTML table with merged header cells and grouped sections
            html_table = """
            <style>
                .capability-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-family: Arial, sans-serif;
                    font-size: 13px;
                }}
                .capability-table th, .capability-table td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: center;
                }}
                .capability-table th {{
                    background-color: #f0f0f0;
                    font-weight: bold;
                }}
                .section-header {{
                    background-color: #e3f2fd;
                    font-weight: bold;
                    text-align: center;
                }}
                .type-column {{
                    text-align: left;
                    background-color: #f9f9f9;
                    font-weight: bold;
                }}
                .total-column {{
                    background-color: #fff9c4;
                    font-weight: bold;
                    font-size: 16px;
                }}
                .sub-header {{
                    background-color: #eeeeee;
                    font-size: 11px;
                }}
            </style>
            
            <table class="capability-table">
                <!-- Main header row with sections -->
                <tr>
                    <th rowspan="2" style="vertical-align: middle;">Issue Type</th>
                    <th colspan="4" class="section-header">📋 Backlog</th>
                    <th colspan="4" class="section-header">🏃 Sprint</th>
                    <th rowspan="2" class="section-header" style="vertical-align: middle;">📊 Total</th>
                    <th colspan="2" class="section-header">📈 30-Day Activity</th>
                </tr>
                <!-- Sub-header row -->
                <tr>
                    <td class="sub-header">Crit</td>
                    <td class="sub-header">High</td>
                    <td class="sub-header">Med</td>
                    <td class="sub-header">Low</td>
                    <td class="sub-header">Crit</td>
                    <td class="sub-header">High</td>
                    <td class="sub-header">Med</td>
                    <td class="sub-header">Low</td>
                    <td class="sub-header">Added</td>
                    <td class="sub-header">Resolved</td>
                </tr>
                <!-- Defects row -->
                <tr>
                    <td class="type-column">Defects</td>
                    <td>{backlog_crit_d}</td>
                    <td>{backlog_high_d}</td>
                    <td>{backlog_med_d}</td>
                    <td>{backlog_low_d}</td>
                    <td>{sprint_crit_d}</td>
                    <td>{sprint_high_d}</td>
                    <td>{sprint_med_d}</td>
                    <td>{sprint_low_d}</td>
                    <td class="total-column">{total_d_with_arrow}</td>
                    <td>{added_d_with_arrow}</td>
                    <td>{resolved_d_with_arrow}</td>
                </tr>
                <!-- Features row -->
                <tr>
                    <td class="type-column">Features</td>
                    <td>{backlog_crit_f}</td>
                    <td>{backlog_high_f}</td>
                    <td>{backlog_med_f}</td>
                    <td>{backlog_low_f}</td>
                    <td>{sprint_crit_f}</td>
                    <td>{sprint_high_f}</td>
                    <td>{sprint_med_f}</td>
                    <td>{sprint_low_f}</td>
                    <td class="total-column">{total_f_with_arrow}</td>
                    <td>{added_f_with_arrow}</td>
                    <td>{resolved_f_with_arrow}</td>
                </tr>
                <!-- Total row -->
                <tr style="background-color: #9fb6d4; color: white; font-weight: bold; font-size: 14px; text-align: center;">
                    <td style="text-align: center; font-weight: bold;">📊 Total</td>
                    <td>{total_backlog_crit}</td>
                    <td>{total_backlog_high}</td>
                    <td>{total_backlog_med}</td>
                    <td>{total_backlog_low}</td>
                    <td>{total_sprint_crit}</td>
                    <td>{total_sprint_high}</td>
                    <td>{total_sprint_med}</td>
                    <td>{total_sprint_low}</td>
                    <td style="background-color: #c4ac2b; color: #3d5a80; font-size: 16px;">{grand_total}</td>
                    <td>{total_added}</td>
                    <td>{total_resolved}</td>
                </tr>
            </table>
            """
            
            # Calculate totals for each column
            total_backlog_crit = defect_data.get('Backlog Critical', 0) + feature_data.get('Backlog Critical', 0)
            total_backlog_high = defect_data.get('Backlog High', 0) + feature_data.get('Backlog High', 0)
            total_backlog_med = defect_data.get('Backlog Medium', 0) + feature_data.get('Backlog Medium', 0)
            total_backlog_low = defect_data.get('Backlog Low', 0) + feature_data.get('Backlog Low', 0)
            total_sprint_crit = defect_data.get('Sprint Critical', 0) + feature_data.get('Sprint Critical', 0)
            total_sprint_high = defect_data.get('Sprint High', 0) + feature_data.get('Sprint High', 0)
            total_sprint_med = defect_data.get('Sprint Medium', 0) + feature_data.get('Sprint Medium', 0)
            total_sprint_low = defect_data.get('Sprint Low', 0) + feature_data.get('Sprint Low', 0)
            grand_total = defect_data.get('Total', 0) + feature_data.get('Total', 0)
            total_added = defect_data.get('Added in last 30 days', 0) + feature_data.get('Added in last 30 days', 0)
            total_resolved = defect_data.get('Resolved in last 30 days', 0) + feature_data.get('Resolved in last 30 days', 0)
            
            # Get last week's data for comparison
            historical_data = get_component_capability_status_historical(jira, jira_config['project_key'], component_name, sprint_id, days_ago=7)
            
            # Debug: Check if historical data was retrieved
            if not historical_data:
                st.warning(f"⚠️ Could not retrieve historical data for trend comparison")
            
            # Helper function to generate comparison arrow
            def get_comparison_arrow(current, previous):
                if current > previous:
                    return " <span style='color: #388e3c; font-size: 16px;'>↑</span>"  # Green up arrow
                elif current < previous:
                    return " <span style='color: #388e3c; font-size: 16px;'>↓</span>"  # Green down arrow
                return ""
            
            # Calculate comparisons for all metrics
            if historical_data:
                hist_grand_total = historical_data['Defects'].get('Total', 0) + historical_data['Features'].get('Total', 0)
                hist_total_added = historical_data['Defects'].get('Added in last 30 days', 0) + historical_data['Features'].get('Added in last 30 days', 0)
                hist_total_resolved = historical_data['Defects'].get('Resolved in last 30 days', 0) + historical_data['Features'].get('Resolved in last 30 days', 0)
                
                # Also get defects and features individually for total, added, and resolved
                hist_defects_total = historical_data['Defects'].get('Total', 0)
                hist_features_total = historical_data['Features'].get('Total', 0)
                hist_defects_added = historical_data['Defects'].get('Added in last 30 days', 0)
                hist_features_added = historical_data['Features'].get('Added in last 30 days', 0)
                hist_defects_resolved = historical_data['Defects'].get('Resolved in last 30 days', 0)
                hist_features_resolved = historical_data['Features'].get('Resolved in last 30 days', 0)
                
                grand_total_arrow = get_comparison_arrow(grand_total, hist_grand_total)
                total_added_arrow = get_comparison_arrow(total_added, hist_total_added)
                total_resolved_arrow = get_comparison_arrow(total_resolved, hist_total_resolved)
                
                defects_total_arrow = get_comparison_arrow(defect_data.get('Total', 0), hist_defects_total)
                features_total_arrow = get_comparison_arrow(feature_data.get('Total', 0), hist_features_total)
                defects_added_arrow = get_comparison_arrow(defect_data.get('Added in last 30 days', 0), hist_defects_added)
                features_added_arrow = get_comparison_arrow(feature_data.get('Added in last 30 days', 0), hist_features_added)
                defects_resolved_arrow = get_comparison_arrow(defect_data.get('Resolved in last 30 days', 0), hist_defects_resolved)
                features_resolved_arrow = get_comparison_arrow(feature_data.get('Resolved in last 30 days', 0), hist_features_resolved)
                
                logger.debug(f"Defects Total - Current: {defect_data.get('Total', 0)}, Historical: {hist_defects_total}, Arrow: {defects_total_arrow}")
                logger.debug(f"Defects Added - Current: {defect_data.get('Added in last 30 days', 0)}, Historical: {hist_defects_added}, Arrow: {defects_added_arrow}")
                logger.debug(f"Defects Resolved - Current: {defect_data.get('Resolved in last 30 days', 0)}, Historical: {hist_defects_resolved}, Arrow: {defects_resolved_arrow}")
                logger.debug(f"Features Total - Current: {feature_data.get('Total', 0)}, Historical: {hist_features_total}, Arrow: {features_total_arrow}")
                logger.debug(f"Features Added - Current: {feature_data.get('Added in last 30 days', 0)}, Historical: {hist_features_added}, Arrow: {features_added_arrow}")
                logger.debug(f"Features Resolved - Current: {feature_data.get('Resolved in last 30 days', 0)}, Historical: {hist_features_resolved}, Arrow: {features_resolved_arrow}")
            else:
                grand_total_arrow = ""
                total_added_arrow = ""
                total_resolved_arrow = ""
                defects_total_arrow = ""
                features_total_arrow = ""
                defects_added_arrow = ""
                features_added_arrow = ""
                defects_resolved_arrow = ""
                features_resolved_arrow = ""
            
            # Format values with arrows
            grand_total_display = f"{grand_total}{grand_total_arrow}"
            total_added_display = f"{total_added}{total_added_arrow}"
            total_resolved_display = f"{total_resolved}{total_resolved_arrow}"
            total_d_display = f"{defect_data.get('Total', 0)}{defects_total_arrow}"
            total_f_display = f"{feature_data.get('Total', 0)}{features_total_arrow}"
            added_d_display = f"{defect_data.get('Added in last 30 days', 0)}{defects_added_arrow}"
            resolved_d_display = f"{defect_data.get('Resolved in last 30 days', 0)}{defects_resolved_arrow}"
            added_f_display = f"{feature_data.get('Added in last 30 days', 0)}{features_added_arrow}"
            resolved_f_display = f"{feature_data.get('Resolved in last 30 days', 0)}{features_resolved_arrow}"
            
            # Fill in the values
            html_table = html_table.format(
                # Defects
                backlog_crit_d=defect_data.get('Backlog Critical', 0),
                backlog_high_d=defect_data.get('Backlog High', 0),
                backlog_med_d=defect_data.get('Backlog Medium', 0),
                backlog_low_d=defect_data.get('Backlog Low', 0),
                sprint_crit_d=defect_data.get('Sprint Critical', 0),
                sprint_high_d=defect_data.get('Sprint High', 0),
                sprint_med_d=defect_data.get('Sprint Medium', 0),
                sprint_low_d=defect_data.get('Sprint Low', 0),
                total_d_with_arrow=total_d_display,
                added_d_with_arrow=added_d_display,
                resolved_d_with_arrow=resolved_d_display,
                # Features
                backlog_crit_f=feature_data.get('Backlog Critical', 0),
                backlog_high_f=feature_data.get('Backlog High', 0),
                backlog_med_f=feature_data.get('Backlog Medium', 0),
                backlog_low_f=feature_data.get('Backlog Low', 0),
                sprint_crit_f=feature_data.get('Sprint Critical', 0),
                sprint_high_f=feature_data.get('Sprint High', 0),
                sprint_med_f=feature_data.get('Sprint Medium', 0),
                sprint_low_f=feature_data.get('Sprint Low', 0),
                total_f_with_arrow=total_f_display,
                added_f_with_arrow=added_f_display,
                resolved_f_with_arrow=resolved_f_display,
                # Totals
                total_backlog_crit=total_backlog_crit,
                total_backlog_high=total_backlog_high,
                total_backlog_med=total_backlog_med,
                total_backlog_low=total_backlog_low,
                total_sprint_crit=total_sprint_crit,
                total_sprint_high=total_sprint_high,
                total_sprint_med=total_sprint_med,
                total_sprint_low=total_sprint_low,
                grand_total=grand_total_display,
                total_added=total_added_display,
                total_resolved=total_resolved_display,
            )
            
            # Comprehensive debug information showing all comparisons
            if historical_data:
                with st.expander("🔍 Debug: Week-over-Week Comparisons", expanded=False):
                    debug_cols = st.columns(3)
                    
                    with debug_cols[0]:
                        st.markdown("**DEFECTS**")
                        st.markdown(f"Total: {defect_data.get('Total', 0)} vs {historical_data['Defects'].get('Total', 0)} {defects_total_arrow}", unsafe_allow_html=True)
                        st.markdown(f"Added: {defect_data.get('Added in last 30 days', 0)} vs {historical_data['Defects'].get('Added in last 30 days', 0)} {defects_added_arrow}", unsafe_allow_html=True)
                        st.markdown(f"Resolved: {defect_data.get('Resolved in last 30 days', 0)} vs {historical_data['Defects'].get('Resolved in last 30 days', 0)} {defects_resolved_arrow}", unsafe_allow_html=True)
                    
                    with debug_cols[1]:
                        st.markdown("**FEATURES**")
                        st.markdown(f"Total: {feature_data.get('Total', 0)} vs {historical_data['Features'].get('Total', 0)} {features_total_arrow}", unsafe_allow_html=True)
                        st.markdown(f"Added: {feature_data.get('Added in last 30 days', 0)} vs {historical_data['Features'].get('Added in last 30 days', 0)} {features_added_arrow}", unsafe_allow_html=True)
                        st.markdown(f"Resolved: {feature_data.get('Resolved in last 30 days', 0)} vs {historical_data['Features'].get('Resolved in last 30 days', 0)} {features_resolved_arrow}", unsafe_allow_html=True)
                    
                    with debug_cols[2]:
                        st.markdown("**TOTALS**")
                        st.markdown(f"Grand Total: {grand_total} vs {historical_data['Defects'].get('Total', 0) + historical_data['Features'].get('Total', 0)} {grand_total_arrow}", unsafe_allow_html=True)
                        st.markdown(f"Total Added: {total_added} vs {historical_data['Defects'].get('Added in last 30 days', 0) + historical_data['Features'].get('Added in last 30 days', 0)} {total_added_arrow}", unsafe_allow_html=True)
                        st.markdown(f"Total Resolved: {total_resolved} vs {historical_data['Defects'].get('Resolved in last 30 days', 0) + historical_data['Features'].get('Resolved in last 30 days', 0)} {total_resolved_arrow}", unsafe_allow_html=True)
            
            # Display the HTML table
            st.markdown(html_table, unsafe_allow_html=True)
            
            # Add legend explaining arrows
            legend_html = """
            <div style="font-size: 12px; color: #666; margin-top: 10px; font-style: italic;">
                <strong>Legend:</strong> <br/>
                <span style='color: #388e3c;'>↑ Green up arrow</span> = Increased (more issues compared to 7 days ago) <br/>
                <span style='color: #388e3c;'>↓ Green down arrow</span> = Decreased (fewer issues compared to 7 days ago)
            </div>
            """
            st.markdown(legend_html, unsafe_allow_html=True)
            
            st.divider()
            
            # Display summary information
            st.subheader("📈 Summary")
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                total_defects = capability_data['Defects'].get('Total', 0)
                st.metric("Total Defects", total_defects)
            
            with col2:
                total_features = capability_data['Features'].get('Total', 0)
                st.metric("Total Features", total_features)
            
            with col3:
                backlog_critical_issues = (capability_data['Defects'].get('Backlog Critical', 0) + 
                                          capability_data['Features'].get('Backlog Critical', 0))
                st.metric("Backlog Critical", backlog_critical_issues)
            
            with col4:
                backlog_high_issues = (capability_data['Defects'].get('Backlog High', 0) + 
                                      capability_data['Features'].get('Backlog High', 0))
                st.metric("Backlog High", backlog_high_issues)
            
            with col5:
                critical_issues = (capability_data['Defects'].get('Sprint Critical', 0) + 
                                 capability_data['Features'].get('Sprint Critical', 0))
                st.metric("Sprint Critical", critical_issues)
            
            with col6:
                high_issues = (capability_data['Defects'].get('Sprint High', 0) + 
                             capability_data['Features'].get('Sprint High', 0))
                st.metric("Sprint High", high_issues)
        
            st.divider()
            
            # Display details section for Critical & High tickets
            st.subheader("🔴 Details - Critical & High Tickets")
            
            # Create tabs for Sprint and Backlog (Sprint first)
            tab_sprint, tab_backlog = st.tabs(["🏃 Sprint", "📋 Backlog"])
            
            # SPRINT DETAILS (First tab)
            with tab_sprint:
                st.write("**Critical and High Priority Issues in Sprint**")
                
                with st.spinner("Fetching sprint critical/high issues..."):
                    sprint_issues = get_critical_high_issues(jira, jira_config['project_key'], component_name, sprint_id, sprint_only=True)
                
                if sprint_issues:
                    jira_url = jira_config['url'].rstrip('/')
                    
                    # Build styled HTML table with clickable issue links
                    html_table = """<style>
.details-table {
    width: 100%;
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 13px;
}
.details-table th {
    background-color: #f0f0f0;
    border: 1px solid #ddd;
    padding: 10px;
    font-weight: bold;
    text-align: left;
}
.details-table td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
    word-wrap: break-word;
    max-width: 300px;
}
.details-table a {
    color: #1f77b4;
    text-decoration: none;
    font-weight: bold;
}
.details-table a:hover {
    text-decoration: underline;
}
</style>

<table class="details-table">
<tr>
<th>Parent EPIC</th>
<th>Issue</th>
<th>Type</th>
<th>Summary</th>
<th>Priority</th>
<th>Resolution Approach</th>
<th>Target Completion</th>
<th>Target Deployment</th>
</tr>
"""
                    
                    for issue in sprint_issues:
                        # Get fix version info
                        fix_version = 'N/A'
                        if issue.fields.fixVersions:
                            fv = issue.fields.fixVersions[0]
                            release_date = fv.releaseDate if hasattr(fv, 'releaseDate') and fv.releaseDate else 'N/A'
                            fix_version = f"{fv.name} ({release_date})"
                        
                        # Get issue type
                        issue_type = issue.fields.issuetype.name if issue.fields.issuetype else 'N/A'
                        
                        # Get full summary (no truncation)
                        summary = issue.fields.summary
                        
                        # Get Parent EPIC
                        parent_epic_key = None
                        parent_epic_name = 'N/A'
                        
                        # First, check if issue has a parent field (standard Jira parent relationship)
                        if hasattr(issue.fields, 'parent') and issue.fields.parent:
                            try:
                                if hasattr(issue.fields.parent, 'key'):
                                    parent_epic_key = issue.fields.parent.key
                                elif isinstance(issue.fields.parent, dict) and 'key' in issue.fields.parent:
                                    parent_epic_key = issue.fields.parent['key']
                            except (AttributeError, KeyError, TypeError):
                                pass
                        
                        # If no parent, try custom field Epic Link IDs
                        if not parent_epic_key:
                            for field_id in ['customfield_10014', 'customfield_10011', 'customfield_10051']:
                                if hasattr(issue.fields, field_id):
                                    epic_obj = getattr(issue.fields, field_id)
                                    if epic_obj:
                                        try:
                                            # Try to access as object first
                                            if hasattr(epic_obj, 'key'):
                                                parent_epic_key = epic_obj.key
                                            # Then try as dict
                                            elif isinstance(epic_obj, dict) and 'key' in epic_obj:
                                                parent_epic_key = epic_obj['key']
                                            if parent_epic_key:
                                                break
                                        except (AttributeError, KeyError, TypeError):
                                            continue
                        
                        # If we have a parent epic key, fetch its name
                        if parent_epic_key and jira:
                            try:
                                parent_issue = jira.issue(parent_epic_key)
                                parent_epic_name = parent_issue.fields.summary if parent_issue.fields.summary else parent_epic_key
                            except Exception as e:
                                logger.debug(f"Error fetching parent epic {parent_epic_key}: {str(e)}")
                                parent_epic_name = parent_epic_key
                            
                            parent_epic_link = f'<a href="{jira_url}/browse/{parent_epic_key}" target="_blank">{parent_epic_name}</a>'
                        else:
                            parent_epic_link = 'N/A'
                        
                        # Create clickable issue link using HTML anchor
                        issue_link = f'<a href="{jira_url}/browse/{issue.key}" target="_blank">{issue.key}</a>'
                        priority = issue.fields.priority.name if issue.fields.priority else 'N/A'
                        resolution_approach = get_resolution_approach(issue)
                        target_completion = get_target_completion_date(issue, jira=jira, base_url=jira_url)
                        
                        html_table += f"<tr><td>{parent_epic_link}</td><td>{issue_link}</td><td>{issue_type}</td><td>{summary}</td><td>{priority}</td><td>{resolution_approach}</td><td>{target_completion}</td><td>{fix_version}</td></tr>"
                    
                    html_table += "</table>"
                    
                    st.markdown(html_table, unsafe_allow_html=True)
                else:
                    st.info("No critical or high priority issues found in sprint.")
            
            # BACKLOG DETAILS (Second tab)
            with tab_backlog:
                st.write("**Critical and High Priority Issues in Backlog**")
                
                with st.spinner("Fetching backlog critical/high issues..."):
                    backlog_issues = get_critical_high_issues(jira, jira_config['project_key'], component_name, sprint_id, sprint_only=False)
                
                if backlog_issues:
                    jira_url = jira_config['url'].rstrip('/')
                    
                    # Build styled HTML table with clickable issue links
                    html_table = """<style>
.details-table {
    width: 100%;
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 13px;
}
.details-table th {
    background-color: #f0f0f0;
    border: 1px solid #ddd;
    padding: 10px;
    font-weight: bold;
    text-align: left;
}
.details-table td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
    word-wrap: break-word;
    max-width: 300px;
}
.details-table a {
    color: #1f77b4;
    text-decoration: none;
    font-weight: bold;
}
.details-table a:hover {
    text-decoration: underline;
}
</style>

<table class="details-table">
<tr>
<th>Parent EPIC</th>
<th>Issue</th>
<th>Type</th>
<th>Summary</th>
<th>Priority</th>
<th>Resolution Approach</th>
<th>Target Completion</th>
<th>Target Deployment</th>
</tr>
"""
                    
                    for issue in backlog_issues:
                        # Get fix version info
                        fix_version = 'N/A'
                        if issue.fields.fixVersions:
                            fv = issue.fields.fixVersions[0]
                            release_date = fv.releaseDate if hasattr(fv, 'releaseDate') and fv.releaseDate else 'N/A'
                            fix_version = f"{fv.name} ({release_date})"
                        
                        # Get issue type
                        issue_type = issue.fields.issuetype.name if issue.fields.issuetype else 'N/A'
                        
                        # Get full summary (no truncation)
                        summary = issue.fields.summary
                        
                        # Get Parent EPIC
                        parent_epic_key = None
                        parent_epic_name = 'N/A'
                        
                        # First, check if issue has a parent field (standard Jira parent relationship)
                        if hasattr(issue.fields, 'parent') and issue.fields.parent:
                            try:
                                if hasattr(issue.fields.parent, 'key'):
                                    parent_epic_key = issue.fields.parent.key
                                elif isinstance(issue.fields.parent, dict) and 'key' in issue.fields.parent:
                                    parent_epic_key = issue.fields.parent['key']
                            except (AttributeError, KeyError, TypeError):
                                pass
                        
                        # If no parent, try custom field Epic Link IDs
                        if not parent_epic_key:
                            for field_id in ['customfield_10014', 'customfield_10011', 'customfield_10051']:
                                if hasattr(issue.fields, field_id):
                                    epic_obj = getattr(issue.fields, field_id)
                                    if epic_obj:
                                        try:
                                            # Try to access as object first
                                            if hasattr(epic_obj, 'key'):
                                                parent_epic_key = epic_obj.key
                                            # Then try as dict
                                            elif isinstance(epic_obj, dict) and 'key' in epic_obj:
                                                parent_epic_key = epic_obj['key']
                                            if parent_epic_key:
                                                break
                                        except (AttributeError, KeyError, TypeError):
                                            continue
                        
                        # If we have a parent epic key, fetch its name
                        if parent_epic_key and jira:
                            try:
                                parent_issue = jira.issue(parent_epic_key)
                                parent_epic_name = parent_issue.fields.summary if parent_issue.fields.summary else parent_epic_key
                            except Exception as e:
                                logger.debug(f"Error fetching parent epic {parent_epic_key}: {str(e)}")
                                parent_epic_name = parent_epic_key
                            
                            parent_epic_link = f'<a href="{jira_url}/browse/{parent_epic_key}" target="_blank">{parent_epic_name}</a>'
                        else:
                            parent_epic_link = 'N/A'
                        
                        # Create clickable issue link using HTML anchor
                        issue_link = f'<a href="{jira_url}/browse/{issue.key}" target="_blank">{issue.key}</a>'
                        priority = issue.fields.priority.name if issue.fields.priority else 'N/A'
                        resolution_approach = get_resolution_approach(issue)
                        target_completion = get_target_completion_date(issue, jira=jira, base_url=jira_url)
                        
                        html_table += f"<tr><td>{parent_epic_link}</td><td>{issue_link}</td><td>{issue_type}</td><td>{summary}</td><td>{priority}</td><td>{resolution_approach}</td><td>{target_completion}</td><td>{fix_version}</td></tr>"
                    
                    html_table += "</table>"
                    
                    st.markdown(html_table, unsafe_allow_html=True)
                else:
                    st.info("No critical or high priority issues found in backlog.")
            
            st.divider()
            
            # RISK SECTION - Flagged issues
            st.subheader("⚠️ Risk - Flagged Issues")
            
            with st.spinner("Fetching flagged issues..."):
                flagged_issues = get_flagged_issues(jira, jira_config['project_key'], component_name)
            
            if flagged_issues:
                jira_url = jira_config['url'].rstrip('/')
                
                # Build styled HTML table for flagged issues
                html_table = """<style>
.risk-table {
    width: 100%;
    border-collapse: collapse;
    font-family: Arial, sans-serif;
    font-size: 13px;
}
.risk-table th {
    background-color: #ffe8e8;
    border: 1px solid #ffcccc;
    padding: 10px;
    font-weight: bold;
    text-align: left;
    color: #c62828;
}
.risk-table td {
    border: 1px solid #ffcccc;
    padding: 10px;
    text-align: left;
}
.risk-table a {
    color: #1f77b4;
    text-decoration: none;
    font-weight: bold;
}
.risk-table a:hover {
    text-decoration: underline;
}
</style>

<table class="risk-table">
<tr>
<th>Issue</th>
<th>Type</th>
<th>Summary</th>
<th>Priority</th>
<th>Flag Comment/Description</th>
</tr>
"""
                
                for issue in flagged_issues:
                    # Get issue type
                    issue_type = issue.fields.issuetype.name if issue.fields.issuetype else 'N/A'
                    
                    # Format summary (truncate if too long)
                    summary = issue.fields.summary[:50] + ('...' if len(issue.fields.summary) > 50 else '')
                    
                    # Create clickable issue link using HTML anchor
                    issue_link = f'<a href="{jira_url}/browse/{issue.key}" target="_blank">{issue.key}</a>'
                    priority = issue.fields.priority.name if issue.fields.priority else 'N/A'
                    
                    # Get the flagged comment using helper function
                    flag_comment = get_flagged_comment(issue)
                    
                    html_table += f"<tr><td>{issue_link}</td><td>{issue_type}</td><td>{summary}</td><td>{priority}</td><td>{flag_comment}</td></tr>"
                
                html_table += "</table>"
                
                st.markdown(html_table, unsafe_allow_html=True)
            else:
                st.info("✅ No flagged issues found. All systems go!")
        
        else:
            st.error(f"Unable to fetch capability status for {component_name}")
    
    # ========================================================================
    # SPRINT METRICS (Placeholder)
    # ========================================================================
    elif st.session_state.current_page == 'Sprint Metrics':
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
        st.info("This is a placeholder page. Feature coming soon!")
        st.write("This page will display:")
        st.write("- Custom JQL queries")
        st.write("- Exportable reports")
        st.write("- Issue breakdowns")
        st.write("- Team metrics")
    
    # ========================================================================
    # DISPLAY BRANDED FOOTER
    # ========================================================================
    try:
        display_branded_footer()
    except Exception as e:
        logger.error(f"Error displaying footer: {str(e)}")


# ============================================================================
# RUN APPLICATION
# ============================================================================
if __name__ == "__main__":
    main()
