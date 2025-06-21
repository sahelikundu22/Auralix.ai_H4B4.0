# Auralix.ai

**Where Meetings Turn into Momentum**

AI-powered meeting automation that captures, transcribes, and transforms discussions into actionable tasks across Notion, Slack, and GitHub.

---

## 🚀 Features

- **🎙️ Dual Audio Recording**: Chrome extension captures tab + microphone audio + upload file (alternating web app)
- **🤖 AI Processing**: Whisper transcription + Gemini analysis summary
- **📤 Slack Integration**: Instant summaries and daily progress reports
- **📋 Notion Sync**: Automatic task creation and management
- **🐙 GitHub Monitoring**: Auto-update tasks based on commits
- **📊 Progress Tracking**: Daily standup automation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INPUT SOURCES                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   Chrome Extension  |  Web App  |  Mic or File Upload              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI PROCESSING ENGINE                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   Whisper API (Speech to Text)  →  Gemini AI (Analysis summary)    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SLACK INTEGRATION                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   Instant Summary Posting  |  Formatted Reports                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TASK MANAGEMENT (NOTION)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   Task Creation  |  Smart Assignment  |  Status Tracking           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GITHUB MONITORING                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   Commit Tracking  →  Task Matching  →  Auto Status Updates        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROGRESS AGGREGATION                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   Daily Reports (GitHub + Notion)  →  Team Progress  →  Slack      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Quick Start

### 1. **Setup**
```bash
git clone <repo-url>
cd meeting
pip install -r requirements.txt
cd backend/dailysync
python setup_env.py
```

### 2. **Configure**
Create `.env` file with your API keys:
```env
NOTION_TOKEN=your_token
TOKEN_GITHUB=your_token
SLACK_WEBHOOK_URL=your_webhook
GEMINI_API_KEY=your_key
```

### 3. **Run**
```bash
python backend/dailysync/flask_app.py
```

### 4. **Install Extension**
1. Go to `chrome://extensions/`
2. Enable Developer Mode
3. Load unpacked → Select `/extension` folder
4. Allow microphone permissions

---

## 🔄 Workflow

1. **Record** → Chrome extension captures meeting audio
2. **Process** → Whisper transcribes, Gemini analyzes
3. **Share** → Summary posted to Slack
4. **Create** → Tasks auto-created in Notion
5. **Track** → GitHub commits update task status
6. **Report** → Daily progress sent to Slack

---

## 📁 Structure

```
meeting/
├── backend/dailysync/     # Flask app, integrations
├── extension/             # Chrome extension
├── web_app/              # Web interface
└── requirements.txt      # Dependencies
```

---

## 🔗 Integrations

- **📝 Notion**: Task database with auto-assignment
- **💬 Slack**: Instant summaries + daily reports
- **🐙 GitHub**: Commit monitoring + auto-updates
- **🤖 AI**: Whisper transcription + Gemini analysis

---

## 🐛 Support

- **Issues**: Create GitHub issue
- **Docs**: Check inline comments
- **Debug**: Set `DEBUG=1` environment variable

---

**Built with ❤️ for efficient team collaboration**
