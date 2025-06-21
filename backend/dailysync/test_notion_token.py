import os
from dotenv import load_dotenv
import requests

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
url = "https://api.notion.com/v1/users/me"
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}
response = requests.get(url, headers=headers)
print("Token loaded:", NOTION_TOKEN[:10] + "..." if NOTION_TOKEN else None)
print(response.status_code, response.text) 