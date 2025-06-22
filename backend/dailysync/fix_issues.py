#!/usr/bin/env python3
"""
Diagnostic script to fix common issues with Auralix.ai backend
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

def check_package_installation():
    """Check if required packages are properly installed"""
    print("🔍 Checking package installations...")
    
    try:
        import google.generativeai as genai
        print("✅ google-generativeai package is installed")
        
        # Test basic functionality
        try:
            genai.configure(api_key="test")
            print("✅ google-generativeai basic functionality works")
        except Exception as e:
            print(f"⚠️ google-generativeai configuration test failed: {e}")
            
    except ImportError as e:
        print(f"❌ google-generativeai package not found: {e}")
        print("💡 Installing google-generativeai...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai>=0.3.0"])
            print("✅ google-generativeai installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install google-generativeai")

def check_env_variables():
    """Check environment variables"""
    print("\n🔍 Checking environment variables...")
    
    load_dotenv()
    
    required_vars = [
        "NOTION_TOKEN",
        "PARENT_PAGE_ID", 
        "GEMINI_API_KEY",
        "SLACK_BOT_TOKEN",
        "SLACK_CHANNEL_ID",
        "TOKEN_GITHUB",
        "REPO_OWNER",
        "REPO_NAME"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * len(value)} (length: {len(value)})")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Please add these to your .env file")
    
    return len(missing_vars) == 0

def check_notion_database():
    """Check Notion database access"""
    print("\n🔍 Checking Notion database access...")
    
    load_dotenv()
    
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("DATABASE_ID")
    parent_page_id = os.getenv("PARENT_PAGE_ID")
    
    if not notion_token:
        print("❌ NOTION_TOKEN not set")
        return False
    
    if not parent_page_id:
        print("❌ PARENT_PAGE_ID not set")
        return False
    
    import requests
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    
    # Check if parent page exists
    try:
        response = requests.get(f"https://api.notion.com/v1/pages/{parent_page_id}", headers=headers)
        if response.status_code == 200:
            print("✅ Parent page accessible")
        else:
            print(f"❌ Parent page not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing parent page: {e}")
        return False
    
    # Check database if ID exists
    if database_id:
        try:
            response = requests.get(f"https://api.notion.com/v1/databases/{database_id}", headers=headers)
            if response.status_code == 200:
                print("✅ Existing database accessible")
                return True
            else:
                print(f"❌ Database with ID {database_id} not accessible: {response.status_code}")
                print("💡 This database might not exist or isn't shared with your integration")
                return False
        except Exception as e:
            print(f"❌ Error accessing database: {e}")
            return False
    else:
        print("ℹ️ No DATABASE_ID set - will create new database when needed")
        return True

def main():
    """Main diagnostic function"""
    print("🚀 Auralix.ai Backend Diagnostic Tool")
    print("=" * 50)
    
    # Check packages
    check_package_installation()
    
    # Check environment variables
    env_ok = check_env_variables()
    
    # Check Notion access
    notion_ok = check_notion_database()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    
    if env_ok and notion_ok:
        print("✅ All checks passed! Your backend should work correctly.")
        print("\n💡 Next steps:")
        print("1. Start your Flask app: python flask_app.py")
        print("2. If you need a new Notion database, visit: http://localhost:5000/init-db")
        print("3. Test transcription: http://localhost:5000/transcribe")
    else:
        print("❌ Some issues found. Please fix them before running the backend.")
        print("\n💡 Common fixes:")
        print("1. Install missing packages: pip install -r requirements.txt")
        print("2. Check your .env file has all required variables")
        print("3. Ensure your Notion integration has proper permissions")
        print("4. Create a new database if needed: http://localhost:5000/init-db")

if __name__ == "__main__":
    main() 