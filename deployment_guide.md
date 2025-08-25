# 🚀 ActionInbox 24/7 Deployment Guide

## Option 1: Heroku (Recommended - Free Tier Available)

### Step 1: Prepare for Deployment
```bash
# Install Heroku CLI
# Download from: https://devcenter.heroku.com/articles/heroku-cli

# Login to Heroku
heroku login
```

### Step 2: Create Heroku App
```bash
# Create new app
heroku create actioninbox-your-name

# Add environment variables
heroku config:set DISCORD_BOT_TOKEN=your_token
heroku config:set NOTION_API_KEY=your_key
heroku config:set FLASK_SECRET_KEY=your_secret
```

### Step 3: Deploy
```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Initial deployment"

# Deploy to Heroku
git push heroku main

# Scale dynos
heroku ps:scale web=1 worker=1
```

### Step 4: Monitor
```bash
# View logs
heroku logs --tail

# Check status
heroku ps
```

## Option 2: Railway (Modern Alternative)

### Step 1: Setup
1. Go to https://railway.app/
2. Connect your GitHub repository
3. Deploy from GitHub

### Step 2: Environment Variables
Add these in Railway dashboard:
- `DISCORD_BOT_TOKEN`
- `NOTION_API_KEY`
- `FLASK_SECRET_KEY`

## Option 3: Render (Free Tier)

### Step 1: Setup
1. Go to https://render.com/
2. Connect GitHub repository
3. Create Web Service and Background Worker

### Step 2: Configuration
- **Web Service**: `gunicorn web_app:app`
- **Worker Service**: `python clean_discord_bot.py`

## Option 4: VPS (DigitalOcean/AWS/Linode)

### Step 1: Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip nginx -y

# Clone repository
git clone your-repo-url
cd actioninbox
```

### Step 2: Install Dependencies
```bash
# Install Python packages
pip3 install -r requirements.txt

# Create systemd services
sudo nano /etc/systemd/system/actioninbox-web.service
sudo nano /etc/systemd/system/actioninbox-bot.service
```

### Step 3: Systemd Service Files

**Web Service** (`/etc/systemd/system/actioninbox-web.service`):
```ini
[Unit]
Description=ActionInbox Web App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/actioninbox
Environment=PATH=/home/ubuntu/actioninbox/venv/bin
ExecStart=/home/ubuntu/actioninbox/venv/bin/gunicorn --bind 0.0.0.0:8000 web_app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**Bot Service** (`/etc/systemd/system/actioninbox-bot.service`):
```ini
[Unit]
Description=ActionInbox Discord Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/actioninbox
Environment=PATH=/home/ubuntu/actioninbox/venv/bin
ExecStart=/home/ubuntu/actioninbox/venv/bin/python clean_discord_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Step 4: Start Services
```bash
# Enable and start services
sudo systemctl enable actioninbox-web
sudo systemctl enable actioninbox-bot
sudo systemctl start actioninbox-web
sudo systemctl start actioninbox-bot

# Check status
sudo systemctl status actioninbox-web
sudo systemctl status actioninbox-bot
```

## Option 5: Docker Deployment

### Step 1: Create Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "web_app:app"]
```

### Step 2: Docker Compose
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
  
  bot:
    build: .
    command: python clean_discord_bot.py
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
```

## 💰 Cost Comparison

| Platform | Free Tier | Paid Plans | Best For |
|----------|-----------|------------|----------|
| Heroku | 550 hours/month | $7/month | Quick deployment |
| Railway | $5 credit | $0.000463/GB-hour | Modern interface |
| Render | 750 hours/month | $7/month | Simple setup |
| DigitalOcean | $200 credit | $5/month | Full control |
| AWS EC2 | 750 hours/month | $3.5/month | Scalability |

## 🎯 Recommended Setup

**For Hackathon/Demo**: Heroku or Railway (free tier)
**For Production**: DigitalOcean VPS ($5/month)
**For Scale**: AWS with auto-scaling

## 📊 Monitoring & Maintenance

### Health Checks
```python
# Add to web_app.py
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
```

### Log Monitoring
```bash
# Heroku
heroku logs --tail --app your-app-name

# VPS
sudo journalctl -u actioninbox-web -f
sudo journalctl -u actioninbox-bot -f
```

### Backup Strategy
- Database: Daily automated backups
- Code: GitHub repository
- Credentials: Secure environment variables

## 🔒 Security Checklist

- [ ] Environment variables for all secrets
- [ ] HTTPS enabled (Let's Encrypt for VPS)
- [ ] Regular security updates
- [ ] Firewall configured (VPS only)
- [ ] Rate limiting enabled
- [ ] Error logging configured

## 🚀 Quick Deploy Commands

### Heroku One-Click Deploy
```bash
# Clone and deploy in one go
git clone your-repo
cd actioninbox
heroku create actioninbox-$(date +%s)
heroku config:set DISCORD_BOT_TOKEN=your_token
git push heroku main
heroku ps:scale web=1 worker=1
```

Your ActionInbox will be live 24/7! 🎉