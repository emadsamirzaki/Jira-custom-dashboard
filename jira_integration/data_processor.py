"""Data processing and transformation utilities."""

import logging
import streamlit as st
from datetime import datetime
from datetime import timedelta
import re

logger = logging.getLogger(__name__)


def get_target_completion_date(issue, jira=None, base_url=None, debug=False):
    """
    Get the target completion date for an issue.
    Priority:
    1. If due_date exists, return it
    2. If no due_date, try to get sprint end date (if issue is assigned to a sprint)
    3. If not assigned to any sprint, return "N/A"
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
                    flag_time = datetime.fromisoformat(flag_added_time.replace('Z', '+00:00'))
                    closest_comment = None
                    smallest_diff = None
                    
                    for comment in issue.fields.comment.comments:
                        comment_time = datetime.fromisoformat(comment.created.replace('Z', '+00:00'))
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
        logger.error(f"Error retrieving comment: {str(e)}")
        return 'Error retrieving comment'


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
