#!/usr/bin/env python3
"""Basic ActionInbox Demo - Works without any APIs"""

from flask import Flask, render_template, request, jsonify
import json
from action_inbox import process_email_json

app = Flask(__name__)

# Sample emails for demo
SAMPLE_EMAILS = [
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
    }
]

@app.route('/')
def dashboard():
    """Basic dashboard"""
    return render_template('basic_dashboard.html')

@app.route('/api/process-demo')
def process_demo():
    """Process demo emails"""
    try:
        results = []
        
        for email in SAMPLE_EMAILS:
            result = process_email_json(json.dumps(email))
            
            # Parse the result
            lines = result.strip().split('\n')
            analysis_json = ""
            reply_json = ""
            
            in_reply = False
            for line in lines:
                if line.strip().startswith('{"reply"'):
                    in_reply = True
                
                if in_reply:
                    reply_json += line + "\n"
                else:
                    analysis_json += line + "\n"
            
            try:
                analysis = json.loads(analysis_json.strip())
                reply = json.loads(reply_json.strip())
                
                results.append({
                    'email_id': email['message_id'],
                    'email_subject': email['subject'],
                    'email_from': email['from_name'],
                    'analysis': analysis,
                    'reply': reply
                })
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                results.append({
                    'email_id': email['message_id'],
                    'email_subject': email['subject'],
                    'email_from': email['from_name'],
                    'analysis': {'classification': 'FYI', 'confidence': 0.5, 'summary': 'Demo email'},
                    'reply': {'reply': {'subject': 'Re: Demo', 'body': 'Demo reply'}}
                })
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/process-custom', methods=['POST'])
def process_custom():
    """Process custom email input"""
    try:
        email_data = request.json
        result = process_email_json(json.dumps(email_data))
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🚀 ActionInbox Basic Demo Starting...")
    print("📧 No Gmail API needed - uses sample emails")
    print("🌐 Open: http://localhost:5000")
    print("⚡ Ready for demo in 30 seconds!")
    app.run(debug=True, port=5000)