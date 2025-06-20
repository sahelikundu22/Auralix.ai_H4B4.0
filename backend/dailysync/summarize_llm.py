import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash")

def summarize_user_activity(user_commits, user_tasks):
    prompt = f"""Generate a concise standup update in this exact format (no bullet numbers, no extra lines):

✅ What I did:
- [List completed items]

🚧 In progress:
- [List WIP items]

❌ Blockers:
- [List blockers or "None"]

Base this on:
GitHub Commits: {user_commits}
Notion Tasks: {user_tasks}"""

    try:
        response = model.generate_content(prompt)
        # Clean up the response
        summary = response.text.strip()
        # Remove any existing bullet points from LLM output
        summary = summary.replace("• ", "- ")
        # Ensure single newlines
        summary = "\n".join(line.strip() for line in summary.split("\n") if line.strip())
        return summary
    except Exception as e:
        print(f"❌ Summarization error: {e}")
        return "⚠️ Update unavailable (summary error)"
# Example usage
if __name__ == "__main__":
    example_commits = [
        "Added GitHub integration for commit tracking",
        "Fixed bug in Notion task status sync"
    ]

    example_tasks = [
        "Sync GitHub with Notion → Done",
        "Summarizer using Gemini → In Progress",
        "Slack integration → Blocked due to auth"
    ]

    summary = summarize_user_activity(example_commits, example_tasks)
    print("📝 Generated Summary:\n", summary)
