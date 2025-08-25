#!/usr/bin/env python3
"""
ActionInbox Setup Wizard
Guides users through complete setup process for their own Google Cloud project
"""

import os
import json
import webbrowser
from pathlib import Path

def print_header():
    print("=" * 60)
    print("🚀 ActionInbox Setup Wizard")
    print("=" * 60)
    print("This wizard will help you set up ActionInbox with your own Google Cloud project.")
    print("This ensures you have full access without any restrictions.\n")

def create_google_project_guide():
    print("📋 STEP 1: Create Google Cloud Project")
    print("-" * 40)
    
    steps = [
        "1. Go to: https://console.cloud.google.com/",
        "2. Click 'Select a project' → 'New Project'",
        "3. Project name: 'ActionInbox-[YourName]'",
        "4. Click 'Create' and wait for project creation",
        "5. Make sure your new project is selected"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    input("\n✅ Press Enter when you've created your Google Cloud project...")

def enable_gmail_api_guide():
    print("\n📧 STEP 2: Enable Gmail API")
    print("-" * 40)
    
    steps = [
        "1. In Google Cloud Console, go to 'APIs & Services' → 'Library'",
        "2. Search for 'Gmail API'",
        "3. Click on 'Gmail API' and click 'Enable'",
        "4. Wait for API to be enabled"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    input("\n✅ Press Enter when Gmail API is enabled...")

def create_credentials_guide():
    print("\n🔑 STEP 3: Create OAuth Credentials")
    print("-" * 40)
    
    steps = [
        "1. Go to 'APIs & Services' → 'Credentials'",
        "2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'",
        "3. If prompted, configure OAuth consent screen:",
        "   - User Type: External",
        "   - App name: ActionInbox",
        "   - User support email: your email",
        "   - Developer contact: your email",
        "   - Save and continue through all steps",
        "4. Back to Credentials, click 'CREATE CREDENTIALS' → 'OAuth client ID'",
        "5. Application type: 'Desktop application'",
        "6. Name: 'ActionInbox Desktop'",
        "7. Click 'Create'",
        "8. Download the JSON file",
        "9. Rename it to 'credentials.json'",
        f"10. Move it to: {os.getcwd()}"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    input("\n✅ Press Enter when you've downloaded credentials.json...")

def verify_credentials():
    print("\n🔍 STEP 4: Verify Setup")
    print("-" * 40)
    
    creds_path = Path("credentials.json")
    if creds_path.exists():
        print("✅ credentials.json found!")
        try:
            with open(creds_path) as f:
                creds = json.load(f)
                if "installed" in creds and "client_id" in creds["installed"]:
                    print("✅ Credentials file format is correct!")
                    return True
                else:
                    print("❌ Credentials file format is incorrect.")
                    return False
        except json.JSONDecodeError:
            print("❌ Credentials file is not valid JSON.")
            return False
    else:
        print("❌ credentials.json not found in current directory.")
        print(f"   Expected location: {creds_path.absolute()}")
        return False

def setup_discord_bot():
    print("\n🤖 STEP 5: Discord Bot Setup (Optional)")
    print("-" * 40)
    
    choice = input("Do you want to set up Discord bot integration? (y/n): ").lower()
    
    if choice == 'y':
        print("\nDiscord Bot Setup:")
        steps = [
            "1. Go to: https://discord.com/developers/applications",
            "2. Click 'New Application'",
            "3. Name: 'ActionInbox Bot'",
            "4. Go to 'Bot' section",
            "5. Click 'Add Bot'",
            "6. Copy the bot token",
            "7. Go to 'OAuth2' → 'URL Generator'",
            "8. Scopes: 'bot', Permissions: 'Send Messages', 'Read Messages'",
            "9. Copy generated URL and add bot to your Discord server"
        ]
        
        for step in steps:
            print(f"   {step}")
        
        bot_token = input("\nEnter your Discord bot token (or press Enter to skip): ").strip()
        channel_id = input("Enter Discord channel ID for notifications (or press Enter to skip): ").strip()
        
        return bot_token, channel_id
    
    return "", ""

def create_env_file(bot_token="", channel_id=""):
    print("\n📝 STEP 6: Creating Configuration")
    print("-" * 40)
    
    env_content = f"""# ActionInbox - Configuration

# Gmail API (Required)
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json

# Notion Integration (Optional - for task creation)
NOTION_API_KEY=
NOTION_DATABASE_ID=

# Discord Bot Integration
DISCORD_BOT_TOKEN={bot_token}
DISCORD_CHANNEL_ID={channel_id}

# Flask Settings
FLASK_SECRET_KEY=actioninbox-{os.urandom(8).hex()}
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ .env file created successfully!")

def final_instructions():
    print("\n🎉 SETUP COMPLETE!")
    print("=" * 60)
    
    print("\n🚀 How to run ActionInbox:")
    print("1. Discord Bot: python clean_discord_bot.py")
    print("2. Web Interface: python web_app.py")
    print("3. CLI Service: python multi_user_service.py")
    
    print("\n📋 Discord Commands (if bot is set up):")
    commands = [
        "!setup - Connect your Gmail account",
        "!start - Start email monitoring",
        "!check - Check emails now",
        "!status - Check service status",
        "!stop - Stop monitoring"
    ]
    
    for cmd in commands:
        print(f"   {cmd}")
    
    print("\n💡 Tips:")
    print("- First run will ask for Gmail permissions")
    print("- Grant all requested permissions for full functionality")
    print("- Your data stays private - only you have access")
    
    print("\n🆘 Need help? Check README.md or create an issue on GitHub")

def main():
    print_header()
    
    # Step 1: Google Cloud Project
    create_google_project_guide()
    
    # Step 2: Enable Gmail API
    enable_gmail_api_guide()
    
    # Step 3: Create credentials
    create_credentials_guide()
    
    # Step 4: Verify setup
    if not verify_credentials():
        print("\n❌ Setup incomplete. Please complete the credentials setup and run again.")
        return
    
    # Step 5: Discord bot (optional)
    bot_token, channel_id = setup_discord_bot()
    
    # Step 6: Create .env file
    create_env_file(bot_token, channel_id)
    
    # Final instructions
    final_instructions()

if __name__ == "__main__":
    main()