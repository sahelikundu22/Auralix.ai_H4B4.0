import json
import os
from datetime import datetime
from create_notiondb import create_meeting_task_database, add_task_to_database
from dotenv import load_dotenv
import subprocess, sys

load_dotenv()

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
            database_id = create_meeting_task_database()
            if not database_id:
                raise Exception("Failed to create or get Notion database")
        
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
                "assignee": item["assignee"] if item["assignee"] else "Unassigned",
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