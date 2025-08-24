#!/usr/bin/env python3
"""Demo emails for hackathon presentation"""

import json
from action_inbox import process_email_json

# Demo emails for hackathon
DEMO_EMAILS = [
    {
        "message_id": "demo1",
        "subject": "Project Review Meeting Tomorrow",
        "from_name": "Sarah Johnson",
        "from_email": "sarah@company.com",
        "to_email": "you@company.com",
        "cc_emails": "",
        "date": "Mon, 25 Nov 2024 14:30:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "Hi! Can we schedule a 30-min meeting tomorrow at 2 PM to review the Q4 project deliverables? I'll send a Zoom link.",
        "attachments": []
    },
    {
        "message_id": "demo2", 
        "subject": "Please approve budget proposal",
        "from_name": "Finance Team",
        "from_email": "finance@company.com",
        "to_email": "you@company.com",
        "cc_emails": "",
        "date": "Mon, 25 Nov 2024 11:15:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "Please review and approve the attached budget proposal by Friday. Need your signature on the final document.",
        "attachments": [{"filename": "budget_proposal.pdf", "mime": "application/pdf", "text": None}]
    },
    {
        "message_id": "demo3",
        "subject": "Invoice #INV-2024-1123",
        "from_name": "TechVendor Inc",
        "from_email": "billing@techvendor.com", 
        "to_email": "you@company.com",
        "cc_emails": "",
        "date": "Mon, 25 Nov 2024 09:45:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "Please find attached invoice #INV-2024-1123 for software licenses. Total amount: $2,500.00. Payment due in 30 days.",
        "attachments": [{"filename": "invoice_1123.pdf", "mime": "application/pdf", "text": "Invoice #INV-2024-1123\nTotal: $2,500.00\nDue: 30 days"}]
    },
    {
        "message_id": "demo4",
        "subject": "Team Update - New Product Launch",
        "from_name": "Product Manager",
        "from_email": "pm@company.com",
        "to_email": "you@company.com", 
        "cc_emails": "",
        "date": "Mon, 25 Nov 2024 16:20:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "FYI - The new product launch is scheduled for December 15th. Marketing campaign starts next week. No action needed from your end.",
        "attachments": []
    }
]

def run_demo():
    """Run demo for hackathon presentation"""
    print("ActionInbox Demo - Email Processing Agent")
    print("=" * 50)
    
    for i, email in enumerate(DEMO_EMAILS, 1):
        print(f"\nEmail {i}: {email['subject']}")
        print(f"From: {email['from_name']}")
        
        # Process email
        from action_inbox import ActionInbox, EmailData
        agent = ActionInbox()
        
        email_data = EmailData(
            message_id=email['message_id'],
            subject=email['subject'],
            from_name=email['from_name'],
            from_email=email['from_email'],
            to_email=email['to_email'],
            cc_emails=email['cc_emails'],
            date=email['date'],
            recipient_timezone=email['recipient_timezone'],
            message_link=email['message_link'],
            body=email['body'],
            attachments=email['attachments']
        )
        
        analysis, reply = agent.process_email(email_data)
        
        # Show results
        print(f"Classification: {analysis['classification']}")
        print(f"Confidence: {analysis['confidence']:.1%}")
        print(f"Summary: {analysis['summary']}")
        print(f"Actions: {', '.join(analysis['next_actions'])}")
        
        if analysis['entities']['meeting_start']:
            print(f"Meeting: {analysis['entities']['meeting_start']}")
        if analysis['entities']['task_title']:
            print(f"Task: {analysis['entities']['task_title']}")
        if analysis['entities']['invoice_total']:
            print(f"Amount: {analysis['entities']['currency']} {analysis['entities']['invoice_total']}")
        
        print(f"Reply: {reply['reply']['body'][:100]}...")
        print("-" * 50)

if __name__ == "__main__":
    run_demo()