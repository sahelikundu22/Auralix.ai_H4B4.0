from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_apscheduler import APScheduler
import requests
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import whisper
import logging
import uuid
import re
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import tempfile
import shutil
import subprocess

# Import Google Generative AI with error handling
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

# --- Basic Setup ---
load_dotenv()
app = Flask(__name__)
CORS(app)
scheduler = APScheduler()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FFmpeg Setup ---
def find_ffmpeg():
    """Find ffmpeg executable in system PATH or common locations"""
    # Try to find ffmpeg in PATH
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        logger.info(f"Found ffmpeg at: {ffmpeg_path}")
        return ffmpeg_path
    
    # Common Windows locations
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        os.path.expanduser(r"~\ffmpeg\bin\ffmpeg.exe"),
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            logger.info(f"Found ffmpeg at: {path}")
            return path
    
    logger.error("FFmpeg not found! Please install ffmpeg and add it to PATH")
    return None

# Set ffmpeg path for Whisper
ffmpeg_path = find_ffmpeg()
if ffmpeg_path:
    os.environ["FFMPEG_BINARY"] = ffmpeg_path
    logger.info(f"Set FFMPEG_BINARY to: {ffmpeg_path}")
else:
    logger.warning("FFmpeg not found - audio transcription may fail")

# --- API Clients and Models ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PARENT_PAGE_ID = os.getenv("PARENT_PAGE_ID")
TOKEN_GITHUB = os.getenv("TOKEN_GITHUB")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini with proper error handling
gemini_model = None
if GEMINI_API_KEY and GEMINI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info("✅ Gemini model initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini model: {e}")
        gemini_model = None
elif not GEMINI_AVAILABLE:
    logger.warning("⚠️ google-generativeai package not available - AI features will be disabled")
elif not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY not found - AI features will be disabled")

whisper_model = whisper.load_model("base")
slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
GITHUB_HEADERS = {
    "Authorization": f"Bearer {TOKEN_GITHUB}",
    "Accept": "application/vnd.github+json",
}
last_seen_sha = None

# --- Main API Routes ---
@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "message": "Auralix Unified Meeting System",
        "endpoints": {
            "/": "Home page with API status",
            "/health": "Health check",
            "/transcribe": "[POST] Upload audio for transcription and summary",
            "/check-commits": "Manually check GitHub commits and show history",
            "/commit-history": "Show full commit history for the repository",
            "/send-standup": "Manually send daily standup",
            "/init-db": "Manually initialize Notion database",
        },
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    audio_path = None
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        audio_file = request.files["file"]
        meeting_title = request.form.get("meetingTitle", "Untitled Meeting")
        slack_enabled = request.form.get("slackEnabled", "false").lower() == "true"
        notion_enabled = request.form.get("notionEnabled", "false").lower() == "true"

        # Create a temporary file with proper extension
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"temp_audio_{uuid.uuid4()}.wav")
        
        # Ensure the file is properly saved
        audio_file.save(audio_path)
        
        # Verify the file exists and has content
        if not os.path.exists(audio_path):
            return jsonify({"error": "Failed to save audio file"}), 500
            
        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            return jsonify({"error": "Audio file is empty"}), 500

        logger.info(f"Audio file saved to: {audio_path} (size: {file_size} bytes)")
        logger.info("Starting transcription...")
        
        # Use absolute path and ensure it's a string for Whisper
        abs_path = os.path.abspath(audio_path)
        logger.info(f"Using absolute path for Whisper: {abs_path}")
        
        # Verify file still exists before transcription
        if not os.path.exists(abs_path):
            return jsonify({"error": "Audio file not found during transcription"}), 500
        
        # Try to set ffmpeg path if not already set
        if not os.environ.get("FFMPEG_BINARY"):
            ffmpeg_path = find_ffmpeg()
            if ffmpeg_path:
                os.environ["FFMPEG_BINARY"] = ffmpeg_path
                logger.info(f"Set FFMPEG_BINARY to: {ffmpeg_path}")
        
        try:
            result = whisper_model.transcribe(abs_path)
            transcription = result["text"]
            logger.info("Transcription completed.")
        except Exception as whisper_error:
            logger.error(f"Whisper transcription failed: {whisper_error}")
            # Return a helpful error message
            return jsonify({
                "error": "Audio transcription failed. Please ensure ffmpeg is installed and accessible. Error: " + str(whisper_error)
            }), 500

        logger.info("Generating summary...")
        summary = generate_meeting_summary(transcription)
        logger.info("Summary generated.")

        data = {
            "id": str(uuid.uuid4()),
            "title": meeting_title,
            "timestamp": datetime.now().isoformat(),
            "transcript": transcription,
            "summary": summary,
        }

        # Always send to Slack (not just when enabled)
        if slack_client and SLACK_CHANNEL_ID:
            try:
                send_summary_to_slack(data)
                logger.info("✅ Meeting summary sent to Slack")
            except Exception as e:
                logger.error(f"Error sending to Slack: {str(e)}")
        else:
            logger.warning("Slack client or channel ID not configured")

        # Always process Notion tasks and update JSON (not just when enabled)
        if summary.get("structured_data_json"):
            try:
                # Update meeting_summary_input.json with new data
                update_meeting_summary_json(summary["structured_data_json"], meeting_title)
                
                # Only add tasks to existing database if it exists, don't create new one
                add_tasks_to_existing_database(summary["structured_data_json"])
                
                logger.info("✅ Meeting summary processed and JSON updated")
            except Exception as e:
                logger.error(f"Error processing meeting summary: {str(e)}")
        else:
            logger.error("No structured data available for processing")

        return jsonify(data)

    except Exception as e:
        logger.error(f"Error in transcription: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the temporary file
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.info(f"Cleaned up temporary file: {audio_path}")
            except Exception as e:
                logger.warning(f"Could not remove temporary file {audio_path}: {e}")

@app.route('/check-commits')
def manual_check_commits():
    check_github_commits()
    return jsonify({"status": "success", "message": "GitHub commits checked and history displayed"})

@app.route('/commit-history')
def show_commit_history():
    """Show full commit history for the repository"""
    repo_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
    logger.info(f"📂 Showing commit history for: {repo_url}")
    
    commits = get_recent_commits()
    if commits:
        commit_history = []
        for commit in commits:
            commit_info = {
                "sha": commit["sha"][:8],
                "author": commit.get("author", {}).get("login", "Unknown"),
                "date": commit["commit"]["author"]["date"],
                "message": commit["commit"]["message"]
            }
            commit_history.append(commit_info)
            logger.info(f"📝 {commit_info['sha']} by {commit_info['author']} on {commit_info['date']}: {commit_info['message']}")
        
        return jsonify({
            "status": "success", 
            "repository": repo_url,
            "total_commits": len(commits),
            "commits": commit_history
        })
    else:
        return jsonify({
            "status": "error", 
            "message": "Could not fetch commits",
            "repository": repo_url
        })

@app.route('/send-standup')
def manual_send_standup():
    send_daily_standup()
    return jsonify({"status": "success", "message": "Standup sent"})

@app.route('/init-db')
def manual_init_db():
    initialize_database()
    return jsonify({"status": "success", "message": "Database initialized"})


# --- Audio Processing, AI Summarization, and Notifications ---
def generate_meeting_summary(text):
    try:
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found in environment variables")
            return {
                "formatted_text": "❌ **Error**: Google Gemini API key not configured. Please add GEMINI_API_KEY to your .env file.",
                "structured_data_json": None
            }
        
        if not gemini_model:
            logger.error("Gemini model not initialized")
            return {
                "formatted_text": "❌ **Error**: Gemini model not initialized. Please check your GEMINI_API_KEY.",
                "structured_data_json": None
            }

        # Calculate due date (7 days from now)
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        json_prompt = f"""
Analyze this meeting transcript and provide a structured summary in JSON format.
Transcript: {text}
Required format: {{"summary": "...", "topics": [], "action_items": [{{"task": "...", "assignee": "..."}}]}}

Rules: Extract action items and assignees. Do NOT include due dates in the JSON - they will be added automatically. Output ONLY valid JSON.
"""
        json_response = gemini_model.generate_content(json_prompt)
        structured_data_clean = re.sub(r"```(?:json)?", "", json_response.text, flags=re.IGNORECASE).strip()
        structured_data_json = json.loads(structured_data_clean)

        # Add due date to all action items
        for item in structured_data_json.get("action_items", []):
            item["due"] = due_date

        text_prompt = f"""
Analyze this meeting transcript and provide a detailed summary formatted with markdown.
Transcript: {text}
Include:
1. A concise summary.
2. Main topics.
3. Action items.
4. Important details.
"""
        text_response = gemini_model.generate_content(text_prompt)
        formatted_text = text_response.text

        return {"structured_data_json": structured_data_json, "formatted_text": formatted_text}
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return {
            "formatted_text": f"❌ **Error generating summary**: {str(e)}\n\nPlease check your API configuration and try again.",
            "structured_data_json": None
        }

def send_summary_to_slack(data):
    if not slack_client or not SLACK_CHANNEL_ID:
        logger.warning("Slack client or channel ID not configured.")
        return
    try:
        message = f"*Meeting Summary: {data['title']}*\n\n{data['summary']['formatted_text']}"
        slack_client.chat_postMessage(channel=SLACK_CHANNEL_ID, text=message, mrkdwn=True)
        logger.info("✅ Summary sent to Slack.")
    except SlackApiError as e:
        logger.error(f"❌ Error sending summary to Slack: {e}")

def update_meeting_summary_json(summary_data, meeting_title):
    """Update the meeting_summary_input.json file with new meeting data"""
    try:
        # Calculate due date (7 days from now)
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Create the task data structure
        task_data = {
            "github_link": os.getenv("GITHUB_REPO_URL", "https://github.com/sahelikundu22/for_testing"),
            "tasks": []
        }
        
        # Process each action item
        for item in summary_data.get("action_items", []):
            task = {
                "task": item["task"],
                "assignee": item["assignee"] if item["assignee"] else "Unassigned",
                "status": "To Do",
                "due": due_date  # Use calculated due date instead of item["due"]
            }
            task_data["tasks"].append(task)
        
        # Save to meeting_summary_input.json
        json_path = os.path.join(os.path.dirname(__file__), "../whisper_api/meeting_summary_input.json")
        with open(json_path, "w") as f:
            json.dump(task_data, f, indent=2)
        
        logger.info(f"✅ Updated meeting_summary_input.json with {len(task_data['tasks'])} tasks from meeting: {meeting_title}")
        return task_data
        
    except Exception as e:
        logger.error(f"Error updating meeting_summary_input.json: {str(e)}")
        return None

def add_tasks_to_existing_database(summary_json):
    """Add tasks to existing Notion database"""
    try:
        # Check if database already exists
        db_id = os.getenv("DATABASE_ID")
        
        if not db_id:
            logger.info("ℹ️ No existing database found. Tasks will be added when you initialize the database.")
            return
        
        # Calculate due date (7 days from now)
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Add tasks to existing database
        if "action_items" in summary_json and summary_json["action_items"]:
            logger.info(f"📝 Adding {len(summary_json['action_items'])} tasks to existing Notion database...")
            success_count = 0
            for item in summary_json["action_items"]:
                try:
                    add_task_to_database(db_id, {
                        "task": item.get("task", "Untitled Task"),
                        "assignee": item.get("assignee", "Unassigned"),
                        "status": "To Do",
                        "due": due_date,  # Use calculated due date instead of item.get("due")
                    })
                    success_count += 1
                except Exception as task_error:
                    logger.error(f"❌ Failed to add task '{item.get('task', 'Untitled Task')}': {task_error}")
                    continue
            
            if success_count > 0:
                logger.info(f"✅ Successfully added {success_count}/{len(summary_json['action_items'])} tasks to Notion database")
            else:
                logger.error("❌ Failed to add any tasks to Notion database. Please check your database ID and permissions.")
        else:
            logger.info("No action items to add to Notion")
            
    except Exception as e:
        logger.error(f"Error adding tasks to existing database: {str(e)}")
        logger.info("💡 Tip: Run /init-db endpoint to create a new database or check your DATABASE_ID in .env file")
        raise e


# --- Notion Database and Task Management ---
def update_global_env_database_id(db_id):
    ROOT_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
    lines = []
    found = False
    if os.path.exists(ROOT_ENV_PATH):
        with open(ROOT_ENV_PATH, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith('DATABASE_ID='):
                lines[i] = f'DATABASE_ID={db_id}\n'
                found = True; break
    if not found:
        lines.append(f'DATABASE_ID={db_id}\n')
    with open(ROOT_ENV_PATH, 'w') as f:
        f.writelines(lines)
    logger.info(f"✅ DATABASE_ID written to {ROOT_ENV_PATH}")

def create_meeting_task_database():
    url = "https://api.notion.com/v1/databases"
    payload = {"parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},"title": [{"type": "text", "text": {"content": "Meeting Tasks"}}],"properties": {"Task": {"title": {}},"Assignee": {"rich_text": {}},"Status": {"select": {"options": [{"name": "To Do", "color": "red"},{"name": "In Progress", "color": "yellow"},{"name": "Done", "color": "green"}]}},"Due": {"date": {}}}}
    response = requests.post(url, headers=NOTION_HEADERS, json=payload)
    data = response.json()
    if response.status_code == 200:
        db_id = data["id"]
        logger.info("✅ Database created successfully! ID: %s", db_id)
        update_global_env_database_id(db_id)
        return db_id
    else:
        logger.error("❌ Failed to create database: %s", data)
        return None

def add_task_to_database(database_id, task):
    url = "https://api.notion.com/v1/pages"
    properties = {"Task": {"title": [{"type": "text", "text": {"content": task["task"]}}]},"Assignee": {"rich_text": [{"type": "text", "text": {"content": task["assignee"]}}]},"Status": {"select": {"name": task["status"]}}}
    if task.get("due"):
        properties["Due"] = {"date": {"start": task["due"]}}
    payload = {"parent": {"database_id": database_id}, "properties": properties}
    response = requests.post(url, headers=NOTION_HEADERS, json=payload)
    if response.status_code == 200:
        logger.info(f"✅ Added task to Notion: {task['task']}")
    else:
        logger.error(f"❌ Failed to add task to Notion: {response.json()}")

def get_all_tasks():
    database_id = os.getenv("DATABASE_ID")
    if not database_id:
        logger.error("❌ DATABASE_ID not found in environment variables")
        return []
    
    try:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        response = requests.post(url, headers=NOTION_HEADERS)
        if response.status_code == 200:
            return response.json()["results"]
        elif response.status_code == 404:
            logger.error(f"❌ Database with ID {database_id} not found. Please check your DATABASE_ID or run /init-db to create a new database.")
            return []
        else:
            logger.error(f"❌ Failed to retrieve tasks: {response.json()}")
            return []
    except Exception as e:
        logger.error(f"❌ Error accessing Notion database: {e}")
        return []


# --- GitHub Commit Monitoring ---
def get_recent_commits():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    response = requests.get(url, headers=GITHUB_HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error("❌ GitHub API Error: %s - %s", response.status_code, response.json())
        return []

def update_task_status_if_matched(commit_msg):
    tasks = get_all_tasks()
    for task in tasks:
        task_name = task["properties"]["Task"]["title"][0]["text"]["content"].strip().lower()
        if task_name in commit_msg.lower():
            page_id = task["id"]
            current_status = task["properties"]["Status"]["select"]["name"]
            if current_status != "Done":
                payload = {"properties": {"Status": {"select": {"name": "Done"}}}}
                url = f"https://api.notion.com/v1/pages/{page_id}"
                response = requests.patch(url, headers=NOTION_HEADERS, json=payload)
                if response.status_code == 200:
                    logger.info(f"✅ Task '{task_name}' marked as Done.")
                else:
                    logger.error(f"❌ Failed to update task '{task_name}': %s", response.json())


# --- Daily Standup Automation ---
def load_user_mapping():
    path = os.path.join(os.path.dirname(__file__), 'user_mapping.json')
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("user_mapping.json not found, using empty mapping.")
        return {}

def get_user_mapping(github_username=None, notion_name=None):
    for mappings in load_user_mapping().values():
        if (github_username and mappings.get('github_username') == github_username) or \
           (notion_name and mappings.get('notion_name') == notion_name):
            return mappings
    return None

def fetch_github_commits():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    since = (datetime.now() - timedelta(hours=24)).isoformat()
    response = requests.get(url, headers=GITHUB_HEADERS, params={'since': since})
    if response.status_code != 200: return {}
    
    commits_by_user = {}
    for commit in response.json():
        author = commit.get('author')
        if not author: continue
        user_info = get_user_mapping(github_username=author['login'])
        if not user_info: continue
        
        slack_id = user_info['slack_id']
        if slack_id not in commits_by_user:
            commits_by_user[slack_id] = []
        commits_by_user[slack_id].append({"message": commit['commit']['message']})
    return commits_by_user

def fetch_notion_tasks():
    database_id = os.getenv("DATABASE_ID")
    if not database_id: return {}
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=NOTION_HEADERS)
    if response.status_code != 200: return {}
    
    tasks_by_user = {}
    for page in response.json().get('results', []):
        assignee_list = page['properties']['Assignee']['rich_text']
        if not assignee_list: continue
        user_info = get_user_mapping(notion_name=assignee_list[0]['text']['content'])
        if not user_info: continue
        
        slack_id = user_info['slack_id']
        if slack_id not in tasks_by_user:
            tasks_by_user[slack_id] = []
        tasks_by_user[slack_id].append({
            "task": page['properties']['Task']['title'][0]['text']['content'],
            "status": page['properties']['Status']['select']['name']
        })
    return tasks_by_user

def summarize_user_activity(user_commits, user_tasks):
    prompt = f"""Generate a concise standup update in this exact format (no bullet numbers, no extra lines):\n\n✅ What I did:\n- [List completed items]\n\n🚧 In progress:\n- [List WIP items]\n\n❌ Blockers:\n- [List blockers or \"None\"]\n\nBase this on:\nGitHub Commits: {user_commits}\nNotion Tasks: {user_tasks}"""
    try:
        response = gemini_model.generate_content(prompt)
        summary = response.text.strip().replace("• ", "- ")
        return "\n".join(line.strip() for line in summary.split("\n") if line.strip())
    except Exception as e:
        logger.error(f"❌ Summarization error: {e}")
        return "⚠️ Update unavailable (summary error)"

def generate_standup_summary():
    commits = fetch_github_commits()
    tasks = fetch_notion_tasks()
    all_users = set(commits.keys()).union(set(tasks.keys()))
    summaries = {}
    
    for slack_id in all_users:
        user_commits = commits.get(slack_id, [])
        user_tasks = tasks.get(slack_id, [])
        if not user_commits and not user_tasks: continue
        
        display_name = next((u['slack_display_name'] for u in load_user_mapping().values() if u['slack_id'] == slack_id), slack_id)
        summaries[display_name] = summarize_user_activity(
            [c['message'] for c in user_commits],
            [f"{t['task']} ({t['status']})" for t in user_tasks]
        )
    return summaries

def format_standup_message(per_user_updates):
    blocks = []
    fallback_text = "📅 Daily Standup Update\n\n"
    for user, summary in per_user_updates.items():
        blocks.extend([
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*👤 {user}*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(line.strip() for line in summary.split("\n") if line.strip())}},
            {"type": "divider"}
        ])
        fallback_text += f"{user}:\n{summary}\n\n"
    return {"text": fallback_text.strip(), "blocks": blocks}

def send_daily_standup_to_slack(per_user_updates):
    if not SLACK_WEBHOOK_URL:
        logger.error("❌ Slack Webhook URL missing!")
        return
    payload = format_standup_message(per_user_updates)
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        logger.info("✅ Standup sent to Slack!")
    else:
        logger.error(f"❌ Slack Error: {response.text}")


# --- Scheduled Jobs & App Initialization ---
def check_github_commits():
    global last_seen_sha
    repo_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
    logger.info(f"🔍 Checking GitHub commits at {datetime.now()}")
    logger.info(f"📂 Repository: {repo_url}")
    commits = get_recent_commits()
    if commits:
        # Show all commits (not just new ones)
        logger.info(f"📋 Found {len(commits)} total commits in repository")
        
        # Process all commits for task matching (not just new ones)
        for commit in commits:
            msg = commit["commit"]["message"]
            author = commit.get("author", {}).get("login", "Unknown")
            date = commit["commit"]["author"]["date"]
            logger.info(f"🔹 Commit by {author} on {date}: {msg}")
            update_task_status_if_matched(msg)
        
        # Update last seen SHA for future reference
        if commits:
            last_seen_sha = commits[0]["sha"]
            logger.info(f"📝 Updated last seen SHA: {last_seen_sha[:8]}...")
    else:
        logger.warning("⚠️ Could not fetch commits.")

def send_daily_standup():
    logger.info(f"📤 Generating and sending daily standup at {datetime.now()}")
    standup_data = generate_standup_summary()
    if not standup_data:
        logger.warning("⚠️ No activity found for any mapped users.")
        return
    send_daily_standup_to_slack(standup_data)

def initialize_database():
    logger.info("🚀 Creating new Notion database...")
    db_id = create_meeting_task_database()
    if db_id:
        # Load tasks from meeting_summary_input.json and add them to the new database
        json_path = os.path.join(os.path.dirname(__file__), "../whisper_api/meeting_summary_input.json")
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            for task in data.get("tasks", []):
                task["status"] = "To Do"
                add_task_to_database(db_id, task)
            logger.info(f"✅ Added {len(data.get('tasks', []))} tasks to new database")
        except FileNotFoundError:
            logger.warning("meeting_summary_input.json not found, skipping initial task population.")
        except Exception as e:
            logger.error(f"Error adding tasks to database: {str(e)}")
    else:
        logger.error("❌ Failed to create new database")
    
    load_dotenv(override=True)

def setup_scheduler():
    scheduler.init_app(app)
    scheduler.add_job(id='check_github_commits', func=check_github_commits, trigger='interval', minutes=5)
    scheduler.add_job(id='send_daily_standup', func=send_daily_standup, trigger='cron', hour=9, minute=0)
    scheduler.start()
    logger.info("⏰ Scheduler started with jobs for GitHub checks and daily standups.")

if __name__ == "__main__":
    setup_scheduler()
    app.run(host="0.0.0.0", port=5000, debug=False)
