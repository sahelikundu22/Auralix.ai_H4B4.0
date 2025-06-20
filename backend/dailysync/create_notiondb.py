import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PARENT_PAGE_ID = os.getenv("PARENT_PAGE_ID")

def create_meeting_task_database():
    url = "https://api.notion.com/v1/databases"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": { "type": "page_id", "page_id": PARENT_PAGE_ID },
        "title": [{ "type": "text", "text": { "content": "Meeting Tasks" } }],
        "properties": {
            "Task": { "title": {} },
            "Assignee": { "rich_text": {} },
            "Status": {
                "select": {
                    "options": [
                        { "name": "To Do", "color": "red" },
                        { "name": "In Progress", "color": "yellow" },
                        { "name": "Done", "color": "green" }
                    ]
                }
            },
            "Due": { "date": {} }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    
    if response.status_code == 200:
        db_id = data["id"]
        print("✅ Database created successfully!")
        print("📁 Database ID:", db_id)

        with open(".env", "a") as env_file:
            env_file.write(f"\nDATABASE_ID={db_id}")

        return db_id
    else:
        print("❌ Failed to create database:", data)
        return None

def add_task_to_database(database_id, task):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": { "database_id": database_id },
        "properties": {
            "Task": {
                "title": [{ "type": "text", "text": { "content": task["task"] } }]
            },
            "Assignee": {
                "rich_text": [{ "type": "text", "text": { "content": task["assignee"] } }]
            },
            "Status": {
                "select": { "name": task["status"] }
            },
            "Due": {
                "date": { "start": task["due"] }
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"✅ Added task: {task['task']}")
    else:
        print(f"❌ Failed to add task '{task['task']}':", response.json())

# --- MAIN FLOW ---
if __name__ == "__main__":
    db_id = create_meeting_task_database()

    if db_id:
        with open("../whisper_api/meeting_summary_input.json", "r") as f:
            data = json.load(f)

        for task in data["tasks"]:
            task["status"] = "To Do"
            add_task_to_database(db_id, task)
