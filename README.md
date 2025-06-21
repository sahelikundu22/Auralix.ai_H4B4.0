# Meeting Task Management System

A comprehensive meeting task management system that integrates Notion, GitHub, and Slack to automatically track and manage action items from meetings. This system uses AI-powered transcription and summarization to extract tasks and automatically syncs them with your project management workflow.

## 🚀 Features

- **AI-Powered Meeting Transcription**: Uses OpenAI Whisper for accurate meeting transcription
- **Intelligent Task Extraction**: Leverages Google Gemini AI to extract action items from meeting transcripts
- **Notion Integration**: Automatically creates and manages tasks in Notion databases
- **GitHub Sync**: Monitors commits and automatically updates task status based on commit messages
- **Slack Notifications**: Sends notifications to Slack channels for task updates
- **Smart User Mapping**: Intelligently maps meeting participants to Notion users
- **Real-time Monitoring**: Continuously monitors GitHub activity for task completion

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Meeting       │    │   AI Processing │    │   Task          │
│   Recording     │───▶│   (Whisper +    │───▶│   Management    │
│                 │    │    Gemini)      │    │   (Notion)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────┐            │
                       │   GitHub        │◀───────────┘
                       │   Monitoring    │
                       └─────────────────┘
```

## 📋 Prerequisites

- Python 3.8+
- Notion account with API access
- GitHub account with Personal Access Token
- Slack workspace with webhook access
- Google Gemini API key (optional, for enhanced AI features)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd meeting
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cd backend/dailysync
   python setup_env.py
   ```
   
   This interactive script will prompt you for:
   - Notion Integration Token
   - Notion Parent Page ID
   - GitHub Personal Access Token
   - GitHub Repository details
   - Slack Webhook URL
   - Google Gemini API Key (optional)

4. **Create Notion database** (if you don't have one)
   ```bash
   python create_notiondb.py
   ```

## 🔧 Configuration

### Environment Variables

The system uses the following environment variables (automatically configured by `setup_env.py`):

```env
# Notion Configuration
NOTION_TOKEN=your_notion_integration_token
PARENT_PAGE_ID=your_notion_parent_page_id
DATABASE_ID=your_notion_database_id

# GitHub Configuration
TOKEN_GITHUB=your_github_personal_access_token
REPO_OWNER=your_github_username_or_org
REPO_NAME=your_repository_name

# Slack Configuration
SLACK_WEBHOOK_URL=your_slack_webhook_url

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key
```

### User Mapping

Create a `user_mapping.json` file in the `backend/dailysync/` directory to map meeting participants to Notion users:

```json
{
  "slack_user_id_1": {
    "notion_name": "John Doe",
    "slack_display_name": "john.doe"
  },
  "slack_user_id_2": {
    "notion_name": "Jane Smith",
    "slack_display_name": "jane.smith"
  }
}
```

## 🚀 Usage

### 1. Process Meeting Recordings

```bash
cd backend/dailysync
python notion_integration.py
```

This will:
- Process meeting transcripts
- Extract action items using AI
- Create tasks in Notion
- Assign tasks to participants

### 2. Monitor GitHub Activity

```bash
python github_integration.py
```

This will:
- Monitor your GitHub repository for new commits
- Automatically update task status when commit messages match task names
- Send notifications to Slack

### 3. Start the Web Server

```bash
python main.py
```

This starts the Flask web server for the web interface.

## 📁 Project Structure

```
meeting/
├── backend/
│   └── dailysync/
│       ├── setup_env.py          # Environment setup script
│       ├── create_notiondb.py    # Notion database creation
│       ├── notion_integration.py # Notion task management
│       ├── github_integration.py # GitHub monitoring
│       └── user_mapping.json     # User mapping configuration
├── requirements.txt              # Python dependencies
└── README.md                    # This file
```

## 🔄 Workflow

1. **Meeting Recording**: Record your meeting (audio/video)
2. **Transcription**: System transcribes the meeting using Whisper
3. **AI Analysis**: Gemini AI extracts action items and assigns them to participants
4. **Task Creation**: Tasks are automatically created in Notion with proper assignments
5. **GitHub Monitoring**: System monitors commits and updates task status
6. **Slack Notifications**: Team members receive updates via Slack

## 🤖 AI Features

- **Meeting Transcription**: High-accuracy speech-to-text conversion
- **Task Extraction**: Intelligent identification of action items from conversation
- **Smart Assignment**: Automatic assignment based on participant mentions
- **Due Date Detection**: Extracts and sets appropriate due dates for tasks

## 🔗 Integrations

### Notion
- Creates and manages task databases
- Updates task status automatically
- Tracks assignees and due dates

### GitHub
- Monitors repository commits
- Matches commit messages to task names
- Updates task completion status

### Slack
- Sends task creation notifications
- Updates team on task completion
- Provides real-time status updates

## 🐛 Troubleshooting

### Common Issues

1. **Notion API Errors**
   - Verify your Notion integration token
   - Ensure the integration has access to the parent page
   - Check that the database ID is correct

2. **GitHub API Rate Limits**
   - Use a Personal Access Token with appropriate permissions
   - Consider implementing rate limiting for high-activity repositories

3. **AI Processing Issues**
   - Ensure your Gemini API key is valid
   - Check that audio files are in supported formats
   - Verify internet connectivity for API calls

### Debug Mode

Enable debug logging by setting the `DEBUG` environment variable:

```bash
export DEBUG=1
python github_integration.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review the configuration examples

---

**Built with ❤️ for efficient team collaboration and project management**
