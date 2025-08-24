# 🔧 ActionInbox Setup Guide

## Quick Setup (5 minutes)

### 1. Clone Repository
```bash
git clone https://github.com/Rahul-Raval-2912/ActionInbox-.git
cd ActionInbox-
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Gmail API (Required)
1. Go to: https://console.cloud.google.com/
2. Create project "ActionInbox"
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download as `credentials.json` in project folder

### 4. Setup Discord Bot (Optional)
1. Go to: https://discord.com/developers/applications
2. Create application "ActionInbox"
3. Create bot and copy token
4. Copy `.env.example` to `.env`
5. Add your Discord bot token to `.env`

### 5. Run ActionInbox
```bash
# Discord Bot (Recommended)
python complete_discord_bot.py

# Or Basic Demo (No setup needed)
python basic_demo.py

# Or Web Interface
python web_app.py
```

## Discord Commands
- `!setup` - Setup your Gmail account
- `!start` - Start email monitoring
- `!status` - Check service status
- `!check` - Check emails now
- `!stop` - Stop monitoring

## Security Note
- Never commit `credentials.json`, `token.json`, or `.env` files
- These contain your personal API keys and tokens
- Use `.env.example` as template for configuration