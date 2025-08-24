#!/usr/bin/env python3
"""Quick setup script for ActionInbox"""

import os
import json

def setup_actioninbox():
    """Interactive setup for ActionInbox"""
    print("ActionInbox Quick Setup")
    print("=" * 40)
    
    # Check for credentials.json
    if not os.path.exists('credentials.json'):
        print("Missing credentials.json")
        print("\nTo get Gmail API credentials:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create project -> Enable Gmail API")
        print("3. Create OAuth 2.0 credentials")
        print("4. Download as 'credentials.json'")
        print("5. Place in this folder")
        return False
    
    print("Found credentials.json")
    
    # Test Gmail connection
    try:
        from gmail_connector import GmailConnector
        connector = GmailConnector()
        
        print("Testing Gmail connection...")
        if connector.authenticate():
            print("Gmail connected successfully!")
            
            # Test email processing
            print("Testing email processing...")
            emails = connector.get_unread_emails(1)
            if emails:
                print(f"Found {len(emails)} unread emails")
            else:
                print("No unread emails (that's okay)")
            
            return True
        else:
            print("Gmail authentication failed")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nTry: pip install -r requirements.txt")
        return False

def show_next_steps():
    """Show what to do next"""
    print("\nSetup Complete!")
    print("=" * 40)
    print("Choose how to run ActionInbox:")
    print()
    print("1. Web Dashboard:")
    print("   python web_app.py")
    print("   -> Open http://localhost:5000")
    print()
    print("2. Continuous Processing:")
    print("   python run_production.py")
    print("   -> Auto-processes emails every 30s")
    print()
    print("3. Single Email Test:")
    print("   python test_agent.py")
    print("   -> Test with sample emails")
    print()
    print("Optional Integrations:")
    print("- Notion API -> Create tasks automatically")
    print("- Calendar API -> Schedule meetings")
    print("- Slack Webhook -> Get notifications")

if __name__ == "__main__":
    if setup_actioninbox():
        show_next_steps()
    else:
        print("\nSetup incomplete. Please fix the issues above.")