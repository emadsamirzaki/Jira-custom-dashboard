import yaml
from jira import JIRA
import json

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    jira_config = config['jira']

# Connect to Jira
jira = JIRA(server=jira_config['url'], basic_auth=(jira_config['email'], jira_config['api_token']))

# Get ESP-2887 specifically
issue_key = 'ESP-2887'
try:
    issue = jira.issue(issue_key)
    print(f'========== Issue: {issue.key} ==========\n')
    
    # Get via REST API
    base_url = jira_config['url'].rstrip('/')
    url = f"{base_url}/rest/api/3/issue/{issue.key}"
    
    response = jira._session.get(url)
    if response.status_code == 200:
        data = response.json()
        fields_data = data.get('fields', {})
        
        # Check specific fields
        print("customfield_11486 (full):")
        print(json.dumps(fields_data.get('customfield_11486'), indent=2))
        
        print("\n\ncustomfield_11487 (full):")
        print(json.dumps(fields_data.get('customfield_11487'), indent=2))
                
except Exception as e:
    print(f"Error: {str(e)}")
