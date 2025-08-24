from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
from gmail_connector import GmailConnector
from action_inbox import process_email_json

app = Flask(__name__)
connector = GmailConnector()

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/authenticate')
def authenticate():
    """Authenticate with Gmail"""
    try:
        success = connector.authenticate()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/process-emails')
def process_emails():
    """Process unread emails"""
    try:
        results = connector.process_emails()
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-reply', methods=['POST'])
def send_reply():
    """Send reply email"""
    try:
        data = request.json
        success = connector.send_reply(
            data['to_email'],
            data['subject'],
            data['body']
        )
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/process-single', methods=['POST'])
def process_single_email():
    """Process a single email from JSON"""
    try:
        email_json = request.json
        result = process_email_json(json.dumps(email_json))
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)