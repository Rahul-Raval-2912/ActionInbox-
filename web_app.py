from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import json
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'hackathon-actioninbox-2025')

# Discord server invite link
DISCORD_INVITE = "https://discord.gg/3bsKRQFu"

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/payment')
def payment():
    return render_template('payment.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('profile.html', user=session)

@app.route('/setup-guide')
def setup_guide():
    return render_template('setup_guide.html')

@app.route('/process-payment', methods=['POST'])
def process_payment():
    # Simple payment simulation
    amount = request.form.get('amount')
    if amount == '100':
        session['paid'] = True
        session['user_id'] = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        flash('Payment successful! Here is your Discord invite link.', 'success')
        return render_template('payment_success.html', discord_invite=DISCORD_INVITE)
    else:
        flash('Invalid payment amount. Please pay ₹100.', 'error')
        return redirect(url_for('payment'))

@app.route('/api/create-project', methods=['POST'])
def create_project():
    """API endpoint to help users create Google Cloud project"""
    data = request.json
    project_name = data.get('project_name', 'ActionInbox')
    
    # Generate setup instructions
    instructions = {
        'project_id': f"actioninbox-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'steps': [
            "Go to https://console.cloud.google.com/",
            f"Create new project: {project_name}",
            "Enable Gmail API and Calendar API",
            "Create OAuth 2.0 credentials",
            "Download credentials.json",
            "Join our Discord server for support"
        ]
    }
    
    return jsonify(instructions)

if __name__ == '__main__':
    app.run(debug=True, port=5000)