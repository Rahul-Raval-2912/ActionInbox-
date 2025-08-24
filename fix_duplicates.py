#!/usr/bin/env python3
"""
Fix duplicate emails by manually marking them as processed
"""

import json
import os
from gmail_connector import GmailConnector

def fix_duplicate_emails():
    """Mark current unread emails as processed to stop duplicates"""
    
    print("🔧 Fixing duplicate email issue...")
    
    # Connect to Gmail
    gmail_connector = GmailConnector()
    
    if not gmail_connector.authenticate():
        print("❌ Gmail authentication failed")
        return
    
    try:
        # Get all unread emails
        results = gmail_connector.service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=50
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            print("📭 No unread emails found")
            return
        
        print(f"📧 Found {len(messages)} unread emails")
        
        # Get current processed emails
        processed_emails_file = 'processed_emails.json'
        all_data = {}
        
        if os.path.exists(processed_emails_file):
            with open(processed_emails_file, 'r') as f:
                all_data = json.load(f)
        
        # Use a default user ID (replace with your Discord user ID)
        user_id = "1409163505260826644"  # Replace with your actual Discord user ID
        
        if user_id not in all_data:
            all_data[user_id] = []
        
        processed_set = set(all_data[user_id])
        
        # Add all current unread emails to processed list
        new_processed = 0
        
        for message in messages:
            message_id = message['id']
            
            if message_id not in processed_set:
                processed_set.add(message_id)
                new_processed += 1
                
                # Get email details for display
                email_data = gmail_connector._get_email_data(message_id)
                if email_data:
                    print(f"  ✅ Marked as processed: {email_data.subject}")
        
        # Save updated processed emails
        all_data[user_id] = list(processed_set)
        
        with open(processed_emails_file, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"\\n🎉 Fixed! Marked {new_processed} emails as processed")
        print(f"📊 Total processed emails: {len(processed_set)}")
        print("\\n✅ The duplicate emails should stop appearing now!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_duplicate_emails()