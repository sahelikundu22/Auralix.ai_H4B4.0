import requests
import os
import time
import json
from dotenv import load_dotenv

# Explicitly load the .env file from the project root
ROOT_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(ROOT_ENV_PATH)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
TOKEN_GITHUB = os.getenv("TOKEN_GITHUB")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
DATABASE_ID = os.getenv("DATABASE_ID")

headers_notion = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

headers_github = {
    "Authorization": f"Bearer {TOKEN_GITHUB}",
    "Accept": "application/vnd.github+json"
}

def get_recent_commits():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    response = requests.get(url, headers=headers_github)
    if response.status_code == 200:
        return response.json()
    else:
        print("❌ GitHub API Error:", response.status_code)
        print(response.json())
        return []

def get_all_tasks():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=headers_notion)
    if response.status_code == 200:
        return response.json()["results"]
    else:
        print("❌ Failed to retrieve tasks:", response.json())
        return []

def update_task_status_if_matched(commit_msg):
    tasks = get_all_tasks()
    for task in tasks:
        task_name = task["properties"]["Task"]["title"][0]["text"]["content"].strip().lower()
        page_id = task["id"]
        current_status = task["properties"]["Status"]["select"]["name"]

        if task_name in commit_msg.lower() and current_status != "Done":
            payload = {
                "properties": {
                    "Status": { "select": { "name": "Done" } }
                }
            }
            url = f"https://api.notion.com/v1/pages/{page_id}"
            response = requests.patch(url, headers=headers_notion, json=payload)
            if response.status_code == 200:
                print(f"✅ Task '{task_name}' marked as Done.")
            else:
                print(f"❌ Failed to update task '{task_name}':", response.json())

if __name__ == "__main__":
    last_seen_sha = None
    print("🔁 Monitoring GitHub for new commits...")

    while True:
        commits = get_recent_commits()
        if commits:
            new_commits = []
            for commit in commits:
                if commit["sha"] == last_seen_sha:
                    break
                new_commits.append(commit)

            if new_commits:
                print(f"🆕 {len(new_commits)} new commit(s) found.")
                for commit in reversed(new_commits):  # oldest first
                    msg = commit["commit"]["message"]
                    print("🔹 Processing commit:", msg)
                    update_task_status_if_matched(msg)
                last_seen_sha = commits[0]["sha"]
            else:
                print("⏳ No new commit found.")
        else:
            print("⚠️ Could not fetch commits.")

        time.sleep(10)