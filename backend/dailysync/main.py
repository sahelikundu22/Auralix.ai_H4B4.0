import os
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import requests

load_dotenv()

# Load user mapping
with open('user_mapping.json') as f:
    USER_MAPPING = json.load(f)

# API Headers
NOTION_HEADERS = {
    "Authorization": f"Bearer {os.getenv('NOTION_TOKEN')}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

GITHUB_HEADERS = {
    "Authorization": f"Bearer {os.getenv('TOKEN_GITHUB')}",
    "Accept": "application/vnd.github+json"
}

def get_user_mapping(github_username=None, notion_name=None):
    """Find matching user across all platforms"""
    for user_id, mappings in USER_MAPPING.items():
        if (github_username and mappings.get('github_username') == github_username) or \
           (notion_name and mappings.get('notion_name') == notion_name):
            return mappings
    return None

def fetch_github_commits():
    """Get commits from last 24 hours grouped by user"""
    url = f"https://api.github.com/repos/{os.getenv('REPO_OWNER')}/{os.getenv('REPO_NAME')}/commits"
    since_date = (datetime.now() - timedelta(hours=24)).isoformat()
    params = {'since': since_date}
    
    response = requests.get(url, headers=GITHUB_HEADERS, params=params)
    if response.status_code != 200:
        print(f"❌ GitHub API Error: {response.status_code}")
        return {}

    commits_by_user = {}
    for commit in response.json():
        github_username = commit['author']['login'] if commit['author'] else "unknown"
        user_info = get_user_mapping(github_username=github_username)
        
        if not user_info:
            continue
            
        slack_id = user_info['slack_id']
        if slack_id not in commits_by_user:
            commits_by_user[slack_id] = []
        
        commits_by_user[slack_id].append({
            "message": commit['commit']['message'],
            "url": commit['html_url'],
            "time": commit['commit']['author']['date']
        })
    
    return commits_by_user

def fetch_notion_tasks():
    """Get tasks from Notion grouped by assignee"""
    url = f"https://api.notion.com/v1/databases/{os.getenv('DATABASE_ID')}/query"
    response = requests.post(url, headers=NOTION_HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Notion API Error: {response.status_code}")
        return {}

    tasks_by_user = {}
    for page in response.json().get('results', []):
        assignee = page['properties']['Assignee']['rich_text'][0]['text']['content']
        user_info = get_user_mapping(notion_name=assignee)
        
        if not user_info:
            continue
            
        slack_id = user_info['slack_id']
        if slack_id not in tasks_by_user:
            tasks_by_user[slack_id] = []
        
        tasks_by_user[slack_id].append({
            "task": page['properties']['Task']['title'][0]['text']['content'],
            "status": page['properties']['Status']['select']['name'],
            "url": page['url']
        })
    
    return tasks_by_user

def generate_standup_summary():
    """Generate per-user summaries from GitHub and Notion"""
    commits = fetch_github_commits()
    tasks = fetch_notion_tasks()
    
    all_users = set(commits.keys()).union(set(tasks.keys()))
    summaries = {}
    
    for slack_id in all_users:
        user_commits = commits.get(slack_id, [])
        user_tasks = tasks.get(slack_id, [])
        
        if not user_commits and not user_tasks:
            continue
            
        # Get user display name
        user_display = next(
            (u['slack_display_name'] for u in USER_MAPPING.values() if u['slack_id'] == slack_id),
            slack_id
        )
        
        summaries[user_display] = {
            "commits": [c['message'] for c in user_commits],
            "tasks": [f"{t['task']} ({t['status']})" for t in user_tasks]
        }
    
    return summaries
if __name__ == "__main__":
    from summarize_llm import summarize_user_activity
    from slack_sender import send_to_slack
    
    print("🔄 Gathering standup data...")
    standup_data = generate_standup_summary()
    
    if not standup_data:
        print("⚠️ No activity found for any mapped users")
    else:
        print("📝 Generating summaries...")
        final_summary = {}
        for user, activities in standup_data.items():
            print(f"  - Processing {user}'s activity")
            if activities["commits"] or activities["tasks"]:
                final_summary[user] = summarize_user_activity(
                    activities["commits"],
                    activities["tasks"]
                )
        
        if final_summary:
            print("📤 Sending to Slack...")
            send_to_slack(final_summary)
        else:
            print("⚠️ No summarizable activity found")