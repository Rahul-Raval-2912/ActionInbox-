#!/usr/bin/env python3
"""
Quick Setup for ActionInbox
Automated setup with minimal user interaction
"""

import os
import json
import webbrowser
import time
from pathlib import Path

def quick_setup():
    print("🚀 ActionInbox Quick Setup")
    print("=" * 40)
    
    # Check if already set up
    if Path("credentials.json").exists() and Path(".env").exists():
        print("✅ ActionInbox is already set up!")
        choice = input("Do you want to reconfigure? (y/n): ").lower()
        if choice != 'y':
            return
    
    print("\n📋 This will help you set up ActionInbox in 3 minutes!")
    print("You'll need to:")
    print("1. Create a Google Cloud project (FREE)")
    print("2. Download one file")
    print("3. Run ActionInbox!")
    
    input("\nPress Enter to continue...")
    
    # Open Google Cloud Console
    print("\n🌐 Opening Google Cloud Console...")
    webbrowser.open("https://console.cloud.google.com/projectcreate")
    
    print("\n📋 Quick Steps:")
    print("1. Create project: 'ActionInbox-YourName'")
    print("2. Enable Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com")
    print("3. Create credentials: https://console.cloud.google.com/apis/credentials")
    print("   → CREATE CREDENTIALS → OAuth client ID → Desktop application")
    print("4. Download JSON file as 'credentials.json' to this folder")
    
    # Wait for credentials
    print(f"\n📁 Waiting for credentials.json in: {os.getcwd()}")
    
    while not Path("credentials.json").exists():
        print("⏳ Waiting for credentials.json... (press Ctrl+C to exit)")
        time.sleep(2)
    
    print("✅ credentials.json found!")
    
    # Create basic .env
    env_content = f"""# ActionInbox - Configuration
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
FLASK_SECRET_KEY=actioninbox-{os.urandom(8).hex()}
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Setup complete!")
    print("\n🚀 Run ActionInbox:")
    print("   python clean_discord_bot.py  # Discord bot")
    print("   python web_app.py           # Web interface")

if __name__ == "__main__":
    quick_setup()