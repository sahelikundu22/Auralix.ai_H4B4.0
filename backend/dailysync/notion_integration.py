import json
import os
from datetime import datetime
from create_notiondb import create_meeting_task_database, add_task_to_database
from dotenv import load_dotenv
import subprocess, sys

load_dotenv()
from rapidfuzz import fuzz, process

# Extract all known Notion names from mapping
user_mapping_path = os.path.join(os.path.dirname(__file__), 'user_mapping.json')
with open(user_mapping_path) as f:
    USER_MAPPING = json.load(f)

# Map both Notion names and Slack display names
KNOWN_NAMES = {}
for user in USER_MAPPING.values():
    KNOWN_NAMES[user['notion_name'].lower()] = user['notion_name']
    KNOWN_NAMES[user['slack_display_name'].lower()] = user['notion_name']

def normalize_assignee(name):
    if not name:
        return "Unassigned"
    
    match, score, _ = process.extractOne(name.lower(), KNOWN_NAMES.keys(), scorer=fuzz.ratio)
    return KNOWN_NAMES[match] if score >= 70 else "Unassigned"

def process_meeting_summary(summary_data, meeting_title):
    """
    Process the meeting summary from whisper_api and create tasks in Notion.
    
    Args:
        summary_data (dict): The JSON summary from Gemini
        meeting_title (str): The title of the meeting
    """
    try:
        # Parse the summary data (it comes as a string from Gemini)
        if isinstance(summary_data, str):
            summary_data = json.loads(summary_data)
        
        # Get or create the database ID
        database_id = os.getenv("DATABASE_ID")
        if not database_id:
            raise Exception("DATABASE_ID not found. Please initialize the database first using the 'Initialize Database' button.")
        
        # Create the task data structure
        task_data = {
            "github_link": os.getenv("GITHUB_REPO_URL", ""),  # You can set this in .env
            "tasks": []
        }
        
        # Process each action item and send to Notion directly
        for item in summary_data.get("action_items", []):
            github_link = os.getenv("GITHUB_REPO_URL") or None
            task = {
                "task": item["task"],
                "assignee": normalize_assignee(item["assignee"]),
                #"assignee": item["assignee"] if item["assignee"] else "Unassigned",
                "status": "To Do",
                "due": item["due"] if item["due"] else (datetime.now().strftime("%Y-%m-%d")),
                "github_link": github_link
            }
            task_data["tasks"].append(task)
            # Add task to Notion directly
            print(f"Adding task to Notion: {task['task']} (Assignee: {task['assignee']}, Due: {task['due']})")
            add_task_to_database(database_id, task)
        
        # Save the task data for reference
        with open("meeting_summary_input.json", "w") as f:
            json.dump(task_data, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Created {len(task_data['tasks'])} tasks in Notion",
            "tasks": task_data["tasks"]
        }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        } 