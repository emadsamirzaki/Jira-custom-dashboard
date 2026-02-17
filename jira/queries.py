"""Jira data retrieval queries and functions."""

import logging
import streamlit as st
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
CACHE_TTL = int(os.getenv('CACHE_TTL', 300))  # Default 5 minutes, configurable


def get_project_info(jira, project_key):
    """Retrieve project information from Jira."""
    try:
        project = jira.project(project_key)
        return {
            'name': project.name,
            'key': project.key,
            'description': project.description if hasattr(project, 'description') else 'No description'
        }
    except Exception as e:
        logger.error(f"Error fetching project info: {str(e)}")
        return None


def get_active_sprint(jira, board_id):
    """Retrieve the active/current sprint information from Jira board."""
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
        logger.error(f"Error fetching active sprint: {str(e)}")
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
        logger.error(f"Error fetching component issues count: {str(e)}")
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
        logger.error(f"Error fetching project components: {str(e)}")
        return []


def get_release_versions(jira, project_key):
    """
    Retrieve released and upcoming versions (fix versions) from the project.
    Returns two lists: released_versions and upcoming_versions
    Each version contains: name, description, release_date, status, version_id
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
        released_versions.sort(key=lambda x: x['release_date'], reverse=True)
        
        # Sort upcoming versions by date (soonest first - ascending)
        upcoming_versions.sort(key=lambda x: x['release_date'], reverse=False)
        
        return released_versions[:5], upcoming_versions[:5]  # Return top 5 each
    
    except Exception as e:
        logger.error(f"Error fetching release versions: {str(e)}")
        return [], []


def get_component_details(jira, project_key, component_name, sprint_id=None):
    """Get detailed information about a specific component and its issues."""
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
        logger.error(f"Error fetching component details: {str(e)}")
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
        logger.error(f"Error fetching capability status: {str(e)}")
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
        logger.error(f"Error fetching historical capability status: {str(e)}")
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
        logger.error(f"Error fetching critical/high issues: {str(e)}")
        st.error(f"Error fetching critical/high issues: {str(e)}")
        return None


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
        component_filter = f'AND component = {component.id}'
        jql = f'project = {project_key} {component_filter} AND flagged is not empty AND resolution = Unresolved ORDER BY priority DESC, created DESC'
        
        # Expand changelog and comments to get full comment details
        issues = _jira.search_issues(jql, maxResults=100, expand='changelog,comments')
        
        return issues if issues else None
    
    except Exception as e:
        logger.error(f"Error fetching flagged issues: {str(e)}")
        st.error(f"Error fetching flagged issues: {str(e)}")
        return None
