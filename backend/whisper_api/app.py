from flask import Flask, request, jsonify
import whisper
import os
import google.generativeai as genai
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
from datetime import datetime
import uuid
import sys
import json
import re
from dotenv import load_dotenv

# Add the dailysync directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "dailysync"))
from notion_integration import process_meeting_summary

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Whisper model
model = whisper.load_model("base")

# Initialize Slack client
slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN")) if os.getenv("SLACK_BOT_TOKEN") else None

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load environment variables from .env file
load_dotenv()

@app.route("/transcribe", methods=["POST"])
def transcribe():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        audio_file = request.files["file"]
        meeting_title = request.form.get("meetingTitle", "Untitled Meeting")
        slack_enabled = request.form.get("slackEnabled", "false").lower() == "true"
        notion_enabled = request.form.get("notionEnabled", "false").lower() == "true"

        # Save audio file temporarily
        audio_path = "temp_audio.wav"
        audio_file.save(audio_path)

        # Transcription using Whisper
        logger.info("Starting transcription with Whisper...")
        result = model.transcribe(audio_path)
        transcription = result["text"]
        logger.info("Transcription completed")

        # Generate summary using Gemini
        logger.info("Generating summary with Gemini...")
        summary = generate_summary(transcription)
        logger.info("Summary generated")

        # Create response data
        data = {
            "id": str(uuid.uuid4()),
            "title": meeting_title,
            "timestamp": datetime.now().isoformat(),
            "transcript": transcription,
            "summary": summary
        }

        # Send to Slack if enabled
        if slack_enabled and slack_client:
            try:
                slack_url = send_to_slack(data)
                if slack_url:
                    data["slackUrl"] = slack_url
            except Exception as e:
                logger.error(f"Error sending to Slack: {str(e)}")
                
        # Create Notion tasks if enabled and JSON is valid
        if notion_enabled:
            try:
                if summary["structured_data_json"] is not None:
                    notion_result = process_meeting_summary(summary["structured_data_json"], meeting_title)
                    data["notionTasks"] = notion_result
                else:
                    data["notionError"] = "Gemini did not return valid JSON. Action items not sent to Notion."
            except Exception as e:
                logger.error(f"Error creating Notion tasks: {str(e)}")
                data["notionError"] = str(e)

        # Cleanup
        os.remove(audio_path)

        return jsonify(data)

    except Exception as e:
        logger.error(f"Error in transcription: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_summary(text):
    try:
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        # First get the structured JSON for Notion
        json_prompt = f"""
Please analyze this meeting transcript and provide a structured summary in the following JSON format:

Transcript:
{text}

Required format:
{{
    "summary": "A concise summary of the key points discussed",
    "topics": ["topic1", "topic2", ...],
    "action_items": [
        {{
            "task": "Description of the task",
            "assignee": "Name of person assigned (if mentioned)",
            "due": "YYYY-MM-DD (if mentioned, otherwise null)"
        }},
        ...
    ],
    "important_details": ["detail1", "detail2", ...]
}}

Rules:
1. Extract clear action items with assignees when mentioned
2. Convert any mentioned dates to YYYY-MM-DD format
3. If no assignee is mentioned for a task, use null
4. If no due date is mentioned for a task, use null
5. Make sure the output is valid JSON
6. Do NOT use markdown, do NOT use bullet points, ONLY output valid JSON as specified. Do not include any text before or after the JSON.

Please provide the response in the exact JSON format specified above.
"""
        json_response = model.generate_content(json_prompt)
        structured_data = json_response.text if hasattr(json_response, 'text') else str(json_response)

        # Remove any code block markers (```json ... ```, or ``` ... ```) anywhere in the string
        structured_data_clean = re.sub(r"```(?:json)?", "", structured_data, flags=re.IGNORECASE)
        structured_data_clean = structured_data_clean.replace("```", "").strip()
        print("Final cleaned Gemini output:", structured_data_clean)
        try:
            structured_data_json = json.loads(structured_data_clean)
        except json.JSONDecodeError as e:
            print("Gemini did not return valid JSON. Raw output:")
            print(structured_data)
            structured_data_json = None

        # Then get the formatted text for Slack
        text_prompt = f"""
Please analyze this meeting transcript and provide a detailed summary:

Transcript:
{text}

Please provide:
1. A concise summary of the key points discussed
2. Main topics covered
3. Any action items or decisions made
4. Important details or numbers mentioned

Format the response in a clear, structured way, using markdown for bold headings and bullet points where appropriate.
"""
        text_response = model.generate_content(text_prompt)
        formatted_text = text_response.text if hasattr(text_response, 'text') else str(text_response)

        return {
            "structured_data": structured_data,
            "structured_data_json": structured_data_json,
            "formatted_text": formatted_text
        }
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return {
            "structured_data": "Error generating summary.",
            "structured_data_json": None,
            "formatted_text": "Error generating summary."
        }

def send_to_slack(data):
    try:
        if not slack_client:
            return None

        channel_id = os.getenv("SLACK_CHANNEL_ID")
        if not channel_id:
            return None

        # Format message using the formatted text summary
        message = f"*Meeting Summary: {data['title']}*\n\n"
        message += data['summary']['formatted_text']  # Use the formatted text version
        message += f"\n\n*Full Transcript:*\n```{data['transcript']}```"

        # Send to Slack
        response = slack_client.chat_postMessage(
            channel=channel_id,
            text=message,
            mrkdwn=True
        )
        
        return response['ts']
    except SlackApiError as e:
        logger.error(f"Error sending to Slack: {str(e)}")
        return None

if __name__ == "__main__":
    app.run(debug=True)
