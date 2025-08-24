#!/usr/bin/env python3
"""Test script for ActionInbox agent"""

import json
from action_inbox import process_email_json

def test_meeting_email():
    """Test meeting classification"""
    email = {
        "message_id": "meeting@test.com",
        "subject": "Sync on Tue 11:00 IST",
        "from_name": "Rahul",
        "from_email": "rahul@acme.com",
        "to_email": "user@company.com",
        "cc_emails": "",
        "date": "Mon, 25 Aug 2025 10:00:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "Hi, can we have a 30-min sync on Tuesday at 11:00 IST to discuss Q3 deliverables? I'll send a Google Meet link.",
        "attachments": []
    }
    
    result = process_email_json(json.dumps(email))
    print("=== MEETING EMAIL TEST ===")
    print(result)
    print()

def test_task_email():
    """Test task classification"""
    email = {
        "message_id": "task@test.com",
        "subject": "Please review the Q3 report",
        "from_name": "Manager",
        "from_email": "manager@company.com",
        "to_email": "user@company.com",
        "cc_emails": "",
        "date": "Mon, 25 Aug 2025 14:00:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "Hi, please review the attached Q3 report and provide feedback by Friday. Need your approval on the budget section.",
        "attachments": [{"filename": "Q3_report.pdf", "mime": "application/pdf", "text": None}]
    }
    
    result = process_email_json(json.dumps(email))
    print("=== TASK EMAIL TEST ===")
    print(result)
    print()

def test_invoice_email():
    """Test invoice classification"""
    email = {
        "message_id": "invoice@test.com",
        "subject": "Invoice #12345",
        "from_name": "Vendor Corp",
        "from_email": "billing@vendor.com",
        "to_email": "user@company.com",
        "cc_emails": "",
        "date": "Mon, 25 Aug 2025 16:00:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "Please find attached invoice #12345 for services rendered. Total amount due: $2,500.00. Payment terms: Net 30 days.",
        "attachments": [{"filename": "invoice_12345.pdf", "mime": "application/pdf", "text": "Invoice #12345\nTotal: $2,500.00\nDue Date: 30 days"}]
    }
    
    result = process_email_json(json.dumps(email))
    print("=== INVOICE EMAIL TEST ===")
    print(result)
    print()

def test_spam_email():
    """Test spam classification"""
    email = {
        "message_id": "spam@test.com",
        "subject": "Amazing Deal - 50% Off!",
        "from_name": "Marketing Team",
        "from_email": "promo@deals.com",
        "to_email": "user@company.com",
        "cc_emails": "",
        "date": "Mon, 25 Aug 2025 18:00:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "Don't miss this amazing offer! Click here for 50% off all products. Unsubscribe at the bottom if you don't want these emails.",
        "attachments": []
    }
    
    result = process_email_json(json.dumps(email))
    print("=== SPAM EMAIL TEST ===")
    print(result)
    print()

if __name__ == "__main__":
    test_meeting_email()
    test_task_email()
    test_invoice_email()
    test_spam_email()