import yaml
from jira import JIRA
import json

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    jira_config = config['jira']

# Connect to Jira
jira = JIRA(server=jira_config['url'], basic_auth=(jira_config['email'], jira_config['api_token']))

# Get an issue that SHOULD have Resolution Approach filled in if it's supposed to be there
project_key = jira_config['project_key']
# Try to get an issue from sprint that's in progress or has more details
jql = f'project = {project_key} AND priority IN (Highest, Critical, High) AND assignee is not EMPTY'
issues = jira.search_issues(jql, maxResults=3)

if issues:
    for i, issue in enumerate(issues):
        print(f'\n\n========== Issue {i+1}: {issue.key} ==========\n')
        
        # Get via REST API
        base_url = jira_config['url'].rstrip('/')
        url = f"{base_url}/rest/api/3/issue/{issue.key}"
        
        response = jira._session.get(url)
        if response.status_code == 200:
            data = response.json()
            fields_data = data.get('fields', {})
            
            # Find fields with significant content (likely to be description or custom text fields)
            print('Fields with non-null/non-empty values:')
            for key, value in sorted(fields_data.items()):
                if value is not None and value != '' and value != [] and value != {}:
                    # Skip very large responses
                    value_str = str(value)
                    if len(value_str) > 300:
                        value_str = value_str[:300] + '...'
                    
                    if 'customfield' in key or 'description' in key or 'summary' in key or any(term in str(value).lower() for term in ['resolution', 'approach', 'notes', 'progress']):
                        print(f'\n{key}:')
                        print(f'  {value_str}')





