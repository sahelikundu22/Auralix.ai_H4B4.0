# Auralix Web App - Free Deployment Guide

This is a web app version of Auralix that can be deployed for free without Chrome Web Store fees.

## 🚀 Free Deployment Options

### Option 1: GitHub Pages (Recommended)
**Cost:** FREE
**Setup time:** 5 minutes

1. **Create a new GitHub repository**
2. **Upload the web_app folder contents** to your repository
3. **Enable GitHub Pages:**
   - Go to Settings → Pages
   - Source: Deploy from a branch
   - Branch: main
   - Folder: / (root)
4. **Your app will be live at:** `https://yourusername.github.io/repository-name`

### Option 2: Netlify
**Cost:** FREE
**Setup time:** 3 minutes

1. **Go to [netlify.com](https://netlify.com)**
2. **Drag and drop** the `web_app` folder
3. **Your app will be live immediately** with a random URL
4. **Custom domain:** Add your own domain for free

### Option 3: Vercel
**Cost:** FREE
**Setup time:** 3 minutes

1. **Go to [vercel.com](https://vercel.com)**
2. **Import your GitHub repository**
3. **Deploy automatically** with every push

### Option 4: Firebase Hosting
**Cost:** FREE
**Setup time:** 5 minutes

1. **Install Firebase CLI:** `npm install -g firebase-tools`
2. **Initialize:** `firebase init hosting`
3. **Deploy:** `firebase deploy`

## 🔧 Backend Deployment

For the Flask backend, deploy to:

### Render (Recommended)
**Cost:** FREE tier available
1. **Connect your GitHub repo**
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `python backend/dailysync/flask_app.py`

### Railway
**Cost:** FREE tier available
1. **Connect GitHub repo**
2. **Auto-deploy** from main branch

### Heroku
**Cost:** FREE tier available
1. **Create Procfile:** `web: python backend/dailysync/flask_app.py`
2. **Deploy via CLI or GitHub integration**

## 📝 Configuration

### Update Backend URL
In `web_app/app.js`, change:
```javascript
const FLASK_BACKEND_URL = "http://localhost:5000";
```
To your deployed backend URL:
```javascript
const FLASK_BACKEND_URL = "https://your-backend-url.com";
```

### Environment Variables
Set these in your backend deployment:
- `NOTION_TOKEN`
- `PARENT_PAGE_ID`
- `TOKEN_GITHUB`
- `REPO_OWNER`
- `REPO_NAME`
- `SLACK_WEBHOOK_URL`
- `GEMINI_API_KEY`

## 🌟 Features

### Web App Features:
- ✅ **Microphone Recording** - Record audio directly in browser
- ✅ **File Upload** - Upload audio files
- ✅ **Real-time Status** - Shows backend connection status
- ✅ **Responsive Design** - Works on mobile and desktop
- ✅ **Backend Integration** - All Flask features accessible

### Backend Features:
- ✅ **GitHub Commit Monitoring** - Auto-update Notion tasks
- ✅ **Slack Standup** - Daily automated standup messages
- ✅ **Notion Database** - Task management integration
- ✅ **Scheduled Tasks** - Runs automatically

## 🔗 Quick Start

1. **Deploy the web app** using any option above
2. **Deploy the Flask backend** to Render/Railway/Heroku
3. **Update the backend URL** in `app.js`
4. **Set environment variables** in your backend
5. **Share the web app URL** with users

## 💡 Benefits Over Chrome Extension

- ✅ **No Chrome Web Store fees**
- ✅ **Works on any browser** (Chrome, Firefox, Safari, Edge)
- ✅ **No installation required**
- ✅ **Instant updates** (no extension updates needed)
- ✅ **Mobile friendly**
- ✅ **Easy to share** (just send a URL)

## 🎯 User Experience

Users simply:
1. **Visit your web app URL**
2. **Allow microphone access** (if recording)
3. **Use all features** just like the extension
4. **No downloads or installations needed**

## 📱 Mobile Support

The web app is fully responsive and works on:
- 📱 **Mobile phones**
- 📱 **Tablets**
- 💻 **Desktop computers**
- 🌐 **All modern browsers**

## 🔒 Security

- **HTTPS required** for microphone access
- **CORS configured** for backend communication
- **Environment variables** for sensitive data
- **No data stored locally** (except temporary audio)

## 🚀 Go Live!

Your users can now access Auralix for free without any Chrome Web Store restrictions. Just share the web app URL and they're ready to go! 