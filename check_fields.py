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
    project_key = jira_config['project_key']
    jql = f'sprint = {sprint.id} AND project = {project_key} AND priority IN (Highest, Critical, High)'
    issues = jira.search_issues(jql, maxResults=5)
    
    if issues:
        issue = issues[0]
        print(f'Testing REST API call for {issue.key}:')
        
        # Use REST API to get sprint information
        base_url = jira_config['url'].rstrip('/')
        url = f"{base_url}/rest/api/3/issue/{issue.key}?fields=sprint"
        print(f'URL: {url}')
        
        try:
            response = jira._session.get(url)
            print(f'Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                sprint_field = data.get('fields', {}).get('sprint')
                print(f'Sprint field: {json.dumps(sprint_field, indent=2)}')
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





