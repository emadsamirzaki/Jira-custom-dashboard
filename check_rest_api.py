import yaml
from jira import JIRA
import json

# Load config from YAML
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    jira_config = config['jira']

# Connect to Jira
jira = JIRA(server=jira_config['url'], basic_auth=(jira_config['email'], jira_config['api_token']))

# Fetch an issue from the sprint
board_id = jira_config['board_id']
sprints = jira.sprints(board_id, state='active')

if sprints:
    sprint = sprints[0]
    print(f'Active Sprint: {sprint.name}')
    print(f'  ID: {sprint.id}')
    print(f'  Start: {sprint.startDate}')
    print(f'  End: {sprint.endDate}')
    print()
    
    project_key = jira_config['project_key']
    jql = f'sprint = {sprint.id} AND project = {project_key} AND priority IN (Highest, Critical, High)'
    issues = jira.search_issues(jql, maxResults=5)
    
    if issues:
        issue = issues[0]
        print(f'Testing fields for {issue.key}:')
        
        # Use REST API to get all fields
        base_url = jira_config['url'].rstrip('/')
        url = f"{base_url}/rest/api/3/issue/{issue.key}"
        
        try:
            response = jira._session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                fields_data = data.get('fields', {})
                print(f'\nAll fields available:')
                for key in sorted(fields_data.keys()):
                    if fields_data[key] is not None:
                        value_str = str(fields_data[key])[:80]
                        print(f'  {key}: {value_str}...' if len(str(fields_data[key])) > 80 else f'  {key}: {value_str}')
            else:
                print(f'Error: {response.text}')
        except Exception as e:
            print(f'Exception: {e}')
            import traceback
            traceback.print_exc()
    else:
        print('No high priority issues in sprint')
else:
    print('No active sprints found')
