"""Component Capability Status page with detailed metrics and comparisons."""

import streamlit as st
import logging

from jira_integration.client import get_jira_connection, validate_jira_connection
from jira_integration.queries import (
    get_active_sprint, get_component_capability_status,
    get_component_capability_status_historical, get_critical_high_issues,
    get_flagged_issues
)
from jira_integration.data_processor import (
    get_target_completion_date, get_resolution_approach, get_flagged_comment
)
from ui.utils import display_refresh_button

logger = logging.getLogger(__name__)


def render_capability_comparison_table(capability_data, historical_data, jira_config):
    """Render the capability status comparison table with arrows."""
    
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
    
    return html_table, capability_data


def render_component_capability_page(jira_config, component_name):
    """Render the component capability status page with detailed metrics."""
    
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
        # Get historical data for comparison
        historical_data = get_component_capability_status_historical(jira, jira_config['project_key'], component_name, sprint_id, days_ago=7)
        
        # Render the comparison table
        html_table, cap_data = render_capability_comparison_table(capability_data, historical_data, jira_config)
        
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
        
        # Display details section for Critical & High tickets (SPRINT)
        st.subheader("🔴 Details - Critical & High Tickets (Sprint)")
        
        with st.spinner("Fetching sprint critical/high issues..."):
            sprint_issues = get_critical_high_issues(jira, jira_config['project_key'], component_name, sprint_id, sprint_only=True)
        
        if sprint_issues:
            jira_url = jira_config['url'].rstrip('/')
            
            # Build styled HTML table with clickable issue links
            html_table_sprint = """<style>
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
                
                html_table_sprint += f"<tr><td>{parent_epic_link}</td><td>{issue_link}</td><td>{issue_type}</td><td>{summary}</td><td>{priority}</td><td>{resolution_approach}</td><td>{target_completion}</td><td>{fix_version}</td></tr>"
            
            html_table_sprint += "</table>"
            
            st.markdown(html_table_sprint, unsafe_allow_html=True)
        else:
            st.info("No critical or high priority issues found in sprint.")
        
        st.divider()
        
        # Display details section for Critical & High tickets (BACKLOG)
        st.subheader("🔴 Details - Critical & High Tickets (Backlog)")
        
        with st.spinner("Fetching backlog critical/high issues..."):
            backlog_issues = get_critical_high_issues(jira, jira_config['project_key'], component_name, sprint_id, sprint_only=False)
        
        if backlog_issues:
            jira_url = jira_config['url'].rstrip('/')
            
            # Build styled HTML table with clickable issue links
            html_table_backlog = """<style>
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
                
                # Get Parent EPIC (similar logic as above)
                parent_epic_key = None
                parent_epic_name = 'N/A'
                
                if hasattr(issue.fields, 'parent') and issue.fields.parent:
                    try:
                        if hasattr(issue.fields.parent, 'key'):
                            parent_epic_key = issue.fields.parent.key
                        elif isinstance(issue.fields.parent, dict) and 'key' in issue.fields.parent:
                            parent_epic_key = issue.fields.parent['key']
                    except (AttributeError, KeyError, TypeError):
                        pass
                
                if not parent_epic_key:
                    for field_id in ['customfield_10014', 'customfield_10011', 'customfield_10051']:
                        if hasattr(issue.fields, field_id):
                            epic_obj = getattr(issue.fields, field_id)
                            if epic_obj:
                                try:
                                    if hasattr(epic_obj, 'key'):
                                        parent_epic_key = epic_obj.key
                                    elif isinstance(epic_obj, dict) and 'key' in epic_obj:
                                        parent_epic_key = epic_obj['key']
                                    if parent_epic_key:
                                        break
                                except (AttributeError, KeyError, TypeError):
                                    continue
                
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
                
                # Create clickable issue link
                issue_link = f'<a href="{jira_url}/browse/{issue.key}" target="_blank">{issue.key}</a>'
                priority = issue.fields.priority.name if issue.fields.priority else 'N/A'
                resolution_approach = get_resolution_approach(issue)
                target_completion = get_target_completion_date(issue, jira=jira, base_url=jira_url)
                
                html_table_backlog += f"<tr><td>{parent_epic_link}</td><td>{issue_link}</td><td>{issue_type}</td><td>{summary}</td><td>{priority}</td><td>{resolution_approach}</td><td>{target_completion}</td><td>{fix_version}</td></tr>"
            
            html_table_backlog += "</table>"
            
            st.markdown(html_table_backlog, unsafe_allow_html=True)
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
            html_table_flagged = """<style>
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
                
                # Display full summary
                summary = issue.fields.summary
                
                # Create clickable issue link
                issue_link = f'<a href="{jira_url}/browse/{issue.key}" target="_blank">{issue.key}</a>'
                priority = issue.fields.priority.name if issue.fields.priority else 'N/A'
                
                # Get the flagged comment
                flag_comment = get_flagged_comment(issue)
                
                html_table_flagged += f"<tr><td>{issue_link}</td><td>{issue_type}</td><td>{summary}</td><td>{priority}</td><td>{flag_comment}</td></tr>"
            
            html_table_flagged += "</table>"
            
            st.markdown(html_table_flagged, unsafe_allow_html=True)
        else:
            st.info("✅ No flagged issues found. All systems go!")
    
    else:
        st.error(f"Unable to fetch capability status for {component_name}")
