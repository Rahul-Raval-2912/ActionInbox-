#!/usr/bin/env python3
"""
Clean ActionInbox Discord Bot - Fixed duplicate email issue
"""

import discord
from discord.ext import commands, tasks
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from gmail_connector import GmailConnector
from action_inbox import ActionInbox
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Single service instance (one Gmail account)
gmail_connector = None
email_agent = None
calendar_service = None
monitoring_active = False
processed_emails = set()
user_email = None

# File to store processed emails
PROCESSED_FILE = 'processed_emails_clean.json'

def load_processed_emails():
    """Load processed emails from file"""
    global processed_emails
    try:
        if os.path.exists(PROCESSED_FILE):
            with open(PROCESSED_FILE, 'r') as f:
                data = json.load(f)
                processed_emails = set(data)
                print(f"Loaded {len(processed_emails)} processed emails")
    except Exception as e:
        print(f"Error loading processed emails: {e}")
        processed_emails = set()

def save_processed_emails():
    """Save processed emails to file"""
    try:
        with open(PROCESSED_FILE, 'w') as f:
            json.dump(list(processed_emails), f, indent=2)
        print(f"Saved {len(processed_emails)} processed emails")
    except Exception as e:
        print(f"Error saving processed emails: {e}")

def create_calendar_event(email_data, analysis):
    """Create Google Calendar event for meetings with enhanced features"""
    global calendar_service, user_email
    
    if not calendar_service:
        print("❌ Calendar service not available")
        return {'error': 'Calendar service not available'}
    
    if analysis.get('classification') != 'Meeting':
        print("❌ Not a meeting email")
        return {'error': 'Not classified as meeting'}
    
    try:
        print(f"\n🔍 Creating calendar event for: {email_data.subject}")
        
        # Parse meeting time from email body and subject
        meeting_time = parse_meeting_time(email_data.body, email_data.subject)
        
        if not meeting_time:
            print(f"❌ Could not parse meeting time from: {email_data.subject}")
            return {'error': 'Could not parse meeting time', 'subject': email_data.subject}
        
        # Extract meeting location from email
        location = extract_meeting_location(email_data.body)
        
        # Create enhanced event details
        event_summary = email_data.subject
        if not event_summary.lower().startswith('meeting'):
            event_summary = f"Meeting: {event_summary}"
        
        event_description = f"""📧 Auto-created by ActionInbox

👤 Organizer: {email_data.from_name} <{email_data.from_email}>
⏰ Duration: {meeting_time.get('duration_minutes', 60)} minutes
📅 Parsed Time: {meeting_time.get('parsed_time')} on {meeting_time.get('parsed_date')}

📝 Original Message:
{email_data.body[:400]}{'...' if len(email_data.body) > 400 else ''}

🤖 Processed by ActionInbox AI"""
        
        event_details = {
            'summary': event_summary,
            'description': event_description,
            'start': {
                'dateTime': meeting_time['start'],
                'timeZone': 'Asia/Kolkata'
            },
            'end': {
                'dateTime': meeting_time['end'],
                'timeZone': 'Asia/Kolkata'
            },
            'attendees': [
                {'email': email_data.from_email, 'responseStatus': 'needsAction'},
                {'email': user_email, 'responseStatus': 'accepted'}
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 15},
                    {'method': 'popup', 'minutes': 10},
                    {'method': 'popup', 'minutes': 5}
                ]
            },
            'guestsCanModify': True,
            'guestsCanInviteOthers': True,
            'guestsCanSeeOtherGuests': True
        }
        
        # Add location if found
        if location:
            event_details['location'] = location
            print(f"📍 Location: {location}")
        
        # Add conference data for online meetings
        if any(keyword in email_data.body.lower() for keyword in ['zoom', 'meet', 'teams', 'online']):
            event_details['conferenceData'] = {
                'createRequest': {
                    'requestId': f"actioninbox-{email_data.message_id[:10]}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        
        print(f"📅 Creating event: {event_summary}")
        print(f"⏰ Time: {meeting_time['start']} to {meeting_time['end']}")
        print(f"👥 Attendees: {email_data.from_email}, {user_email}")
        
        # Create the event
        event = calendar_service.events().insert(
            calendarId='primary',
            body=event_details,
            sendUpdates='all',
            conferenceDataVersion=1 if 'conferenceData' in event_details else 0
        ).execute()
        
        event_link = event.get('htmlLink', 'No link available')
        
        success_result = {
            'success': True,
            'event_id': event.get('id'),
            'event_link': event_link,
            'summary': event_summary,
            'start_time': meeting_time['start'],
            'end_time': meeting_time['end'],
            'duration': meeting_time.get('duration_minutes', 60),
            'attendees': [email_data.from_email, user_email],
            'location': location
        }
        
        print(f"✅ Calendar event created successfully!")
        print(f"🔗 Event link: {event_link}")
        print(f"📧 Notification sent to: {email_data.from_email}")
        
        return success_result
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Calendar event creation failed: {error_msg}")
        return {'error': error_msg, 'subject': email_data.subject}

def extract_meeting_location(body):
    """Extract meeting location from email body"""
    import re
    
    body_lower = body.lower()
    
    # Location patterns
    location_patterns = [
        r'(?:location|venue|at|in)\s*:?\s*([^\n\.]{5,50})',
        r'(?:room|office|building)\s*:?\s*([^\n\.]{3,30})',
        r'(?:zoom|teams|meet)\s*:?\s*(https?://[^\s]+)',
        r'(https?://[^\s]*(?:zoom|meet|teams)[^\s]*)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, body_lower)
        if match:
            location = match.group(1).strip()
            if len(location) > 5:  # Valid location
                return location[:100]  # Limit length
    
    # Check for common online meeting indicators
    if any(keyword in body_lower for keyword in ['zoom', 'google meet', 'teams', 'online']):
        return "Online Meeting"
    
    return None

def parse_meeting_time(body, subject=""):
    """Enhanced meeting time parsing with better accuracy"""
    import re
    from datetime import datetime, timedelta
    
    try:
        text = f"{subject} {body}".lower()
        
        print(f"Parsing meeting time from: {text[:200]}...")
        
        # Enhanced time patterns with more variations
        time_patterns = [
            r'(?:at|@)\s*(\d{1,2}):(\d{2})\s*(am|pm)',  # "at 2:30 PM"
            r'(?:at|@)\s*(\d{1,2})\s*(am|pm)',          # "at 2 PM"
            r'(\d{1,2}):(\d{2})\s*(am|pm)',             # "2:30 PM"
            r'(\d{1,2})\s*(am|pm)',                     # "2 PM"
            r'(\d{1,2}):(\d{2})',                       # "14:30" (24h format)
        ]
        
        meeting_hour = None
        meeting_minute = 0
        
        # Try to find time
        for pattern in time_patterns:
            matches = re.findall(pattern, text)
            if matches:
                match = matches[0]  # Take first match
                print(f"Found time pattern: {match}")
                
                if len(match) >= 2:
                    hour = int(match[0])
                    
                    if len(match) >= 3 and match[1].isdigit():
                        minute = int(match[1])
                        ampm = match[2] if len(match) > 2 else None
                    else:
                        minute = 0
                        ampm = match[1] if len(match) > 1 else None
                    
                    # Convert to 24h format
                    if ampm:
                        if 'pm' in ampm.lower() and hour != 12:
                            hour += 12
                        elif 'am' in ampm.lower() and hour == 12:
                            hour = 0
                    
                    meeting_hour = hour
                    meeting_minute = minute
                    break
        
        # If no time found, use default
        if meeting_hour is None:
            print("No time found, using default 2 PM")
            meeting_hour = 14
            meeting_minute = 0
        
        print(f"Parsed time: {meeting_hour}:{meeting_minute:02d}")
        
        # Enhanced date parsing
        meeting_date = datetime.now()
        
        # Date keywords with priority
        date_patterns = [
            ('today', 0),
            ('tomorrow', 1),
            ('day after tomorrow', 2),
            ('next monday', None),
            ('next tuesday', None),
            ('next wednesday', None),
            ('next thursday', None),
            ('next friday', None),
            ('monday', None),
            ('tuesday', None),
            ('wednesday', None),
            ('thursday', None),
            ('friday', None),
        ]
        
        days_to_add = 1  # Default to tomorrow
        
        for keyword, days in date_patterns:
            if keyword in text:
                if days is not None:
                    days_to_add = days
                else:
                    # Handle weekdays
                    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    day_name = keyword.replace('next ', '')
                    
                    if day_name in weekdays:
                        target_weekday = weekdays.index(day_name)
                        current_weekday = meeting_date.weekday()
                        
                        days_ahead = target_weekday - current_weekday
                        if days_ahead <= 0 or 'next' in keyword:
                            days_ahead += 7
                        
                        days_to_add = days_ahead
                
                print(f"Found date keyword: {keyword}, adding {days_to_add} days")
                break
        
        # Create meeting datetime
        meeting_date = meeting_date + timedelta(days=days_to_add)
        meeting_start = meeting_date.replace(
            hour=meeting_hour,
            minute=meeting_minute,
            second=0,
            microsecond=0
        )
        
        # Smart duration detection
        duration_minutes = 60  # Default 1 hour
        
        duration_patterns = [
            r'(\d+)\s*(?:hour|hr)s?',
            r'(\d+)\s*(?:minute|min)s?',
            r'(\d+)h\s*(\d+)m',
            r'for\s+(\d+)\s*(?:hour|hr)s?',
            r'for\s+(\d+)\s*(?:minute|min)s?'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text)
            if match:
                if 'hour' in pattern or 'hr' in pattern:
                    duration_minutes = int(match.group(1)) * 60
                elif 'minute' in pattern or 'min' in pattern:
                    duration_minutes = int(match.group(1))
                elif 'h' in pattern and 'm' in pattern:
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    duration_minutes = hours * 60 + minutes
                
                print(f"Found duration: {duration_minutes} minutes")
                break
        
        # Common meeting durations
        if '30 min' in text or 'half hour' in text:
            duration_minutes = 30
        elif '15 min' in text or 'quick' in text:
            duration_minutes = 15
        elif '2 hour' in text:
            duration_minutes = 120
        
        meeting_end = meeting_start + timedelta(minutes=duration_minutes)
        
        result = {
            'start': meeting_start.isoformat(),
            'end': meeting_end.isoformat(),
            'duration_minutes': duration_minutes,
            'parsed_time': f"{meeting_hour}:{meeting_minute:02d}",
            'parsed_date': meeting_start.strftime('%Y-%m-%d')
        }
        
        print(f"Final meeting time: {result}")
        return result
        
    except Exception as e:
        print(f"Time parsing error: {e}")
        return None

@bot.event
async def on_ready():
    """Bot startup"""
    print(f'Clean ActionInbox Bot is online! Logged in as {bot.user}')
    load_processed_emails()
    print('Commands:')
    print('  !commands - Show all commands')
    print('  !guide - Complete setup guide')
    print('  !steps - Detailed setup steps')
    print('  !links - Quick setup links')
    print('  !setup - Setup Gmail account')
    print('  !start - Start monitoring')
    print('  !check - Check emails now')
    print('  !status - Check status')

@bot.command(name='setup')
async def setup_gmail(ctx):
    """Setup Gmail account and Calendar"""
    global gmail_connector, email_agent, calendar_service, user_email
    
    try:
        await ctx.send("🔧 Setting up Gmail account and Calendar...")
        
        gmail_connector = GmailConnector()
        email_agent = ActionInbox()
        
        if not gmail_connector.authenticate():
            embed = discord.Embed(
                title="🔒 OAuth Access Denied",
                description="ActionInbox needs its own Google Cloud project for each user.",
                color=0xff6b6b
            )
            embed.add_field(
                name="🚀 Quick Solution",
                value="Run: `python setup_wizard.py` in the ActionInbox folder\nThis will guide you through creating your own Google project (FREE)",
                inline=False
            )
            embed.add_field(
                name="⚡ Super Quick",
                value="Run: `python quick_setup.py` for automated setup",
                inline=False
            )
            embed.add_field(
                name="📋 Manual Steps",
                value="1. Go to console.cloud.google.com\n2. Create project 'ActionInbox-YourName'\n3. Enable Gmail API\n4. Create OAuth credentials\n5. Download as credentials.json",
                inline=False
            )
            embed.add_field(
                name="💡 Why This Happens",
                value="Google requires app verification for public use. Creating your own project bypasses this restriction.",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # Get user email
        profile = gmail_connector.service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress', 'Unknown')
        
        # Setup Calendar service
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json')
        
        if creds and creds.valid:
            calendar_service = build('calendar', 'v3', credentials=creds)
        
        embed = discord.Embed(title="✅ Setup Complete", color=0x00ff00)
        embed.add_field(name="Gmail Account", value=user_email, inline=False)
        embed.add_field(name="Calendar", value="✅ Connected" if calendar_service else "❌ Not available", inline=True)
        embed.add_field(name="Next Steps", value="Use `!start` to begin monitoring", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_msg = str(e)
        if "access_denied" in error_msg or "403" in error_msg:
            embed = discord.Embed(
                title="🔒 OAuth Access Denied",
                description="ActionInbox needs its own Google Cloud project for each user.",
                color=0xff6b6b
            )
            embed.add_field(
                name="🚀 Quick Solution",
                value="Run: `python setup_wizard.py` in the ActionInbox folder\nThis will guide you through creating your own Google project (FREE)",
                inline=False
            )
            embed.add_field(
                name="⚡ Super Quick",
                value="Run: `python quick_setup.py` for automated setup",
                inline=False
            )
            embed.add_field(
                name="📋 Manual Steps",
                value="1. Go to console.cloud.google.com\n2. Create project 'ActionInbox-YourName'\n3. Enable Gmail API\n4. Create OAuth credentials\n5. Download as credentials.json",
                inline=False
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Setup failed: {error_msg}")
        print(f"Setup error: {e}")

@bot.command(name='start')
async def start_monitoring(ctx):
    """Start email monitoring"""
    global monitoring_active
    
    if not gmail_connector or not user_email:
        await ctx.send("❌ Please run `!setup` first.")
        return
    
    if monitoring_active:
        await ctx.send("⚠️ Monitoring is already active.")
        return
    
    monitoring_active = True
    
    if not monitor_emails.is_running():
        monitor_emails.start(ctx.channel)
    
    embed = discord.Embed(title="🚀 Email Monitoring Started", color=0x00ff00)
    embed.add_field(name="Gmail Account", value=user_email, inline=False)
    embed.add_field(name="Check Interval", value="60 seconds", inline=True)
    embed.add_field(name="Processed Emails", value=str(len(processed_emails)), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='stop')
async def stop_monitoring(ctx):
    """Stop email monitoring"""
    global monitoring_active
    
    monitoring_active = False
    
    if monitor_emails.is_running():
        monitor_emails.stop()
    
    await ctx.send("🛑 Email monitoring stopped")

@bot.command(name='status')
async def check_status(ctx):
    """Check service status"""
    embed = discord.Embed(title="📊 ActionInbox Status", color=0x0099ff)
    
    embed.add_field(name="Gmail Account", value=user_email or "Not configured", inline=False)
    embed.add_field(name="Monitoring", value="🟢 Active" if monitoring_active else "🔴 Stopped", inline=True)
    embed.add_field(name="Processed Emails", value=str(len(processed_emails)), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='check')
async def check_emails_now(ctx):
    """Check emails now"""
    if not gmail_connector or not user_email:
        await ctx.send("❌ Please run `!setup` first.")
        return
    
    await ctx.send("🔍 Checking emails now...")
    
    try:
        new_emails = get_new_emails()
        
        if not new_emails:
            await ctx.send("📭 No new emails to process")
            return
        
        await ctx.send(f"📧 Processing {len(new_emails)} new emails...")
        
        for email_data in new_emails:
            # Process with AI
            analysis, reply = email_agent.process_email(email_data)
            classification = analysis.get('classification')
            confidence = analysis.get('confidence', 0) * 100
            
            # Create embed
            embed = discord.Embed(title="📧 Email Processed", color=0x00ff00)
            embed.add_field(name="Subject", value=email_data.subject, inline=False)
            embed.add_field(name="From", value=f"{email_data.from_name} <{email_data.from_email}>", inline=False)
            embed.add_field(name="Classification", value=f"{classification} ({confidence:.0f}%)", inline=True)
            
            # Handle meetings with enhanced calendar integration
            if classification == 'Meeting':
                embed.color = 0xff9900
                calendar_result = create_calendar_event(email_data, analysis)
                
                if calendar_result and calendar_result.get('success'):
                    embed.add_field(name="✅ Calendar Event Created", value=f"""
**Time:** {calendar_result.get('start_time', 'Unknown')}
**Duration:** {calendar_result.get('duration', 60)} minutes
**Attendees:** {len(calendar_result.get('attendees', []))} people
**Location:** {calendar_result.get('location', 'Not specified')}
📧 Notification sent to organizer
""", inline=False)
                    
                    if calendar_result.get('event_link'):
                        embed.add_field(name="🔗 Event Link", value=f"[Open in Calendar]({calendar_result['event_link']})", inline=False)
                
                elif calendar_result and calendar_result.get('error'):
                    error_msg = str(calendar_result['error'])
                    if "unregistered callers" in error_msg or "API Key" in error_msg:
                        embed.add_field(name="⚠️ Calendar Setup Needed", value=f"""
📅 Meeting detected but Calendar API not enabled:
**Solution:** Use `!guide` and enable Calendar API in your Google Cloud project
**Quick Link:** [Enable Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
""", inline=False)
                    else:
                        embed.add_field(name="⚠️ Calendar Issue", value=f"""
📅 Meeting detected but calendar event failed:
**Error:** {error_msg}
**Fix:** Use `!fix_calendar` for troubleshooting
""", inline=False)
                else:
                    embed.add_field(name="Type", value="📅 Meeting detected (calendar not available)", inline=True)
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error checking emails: {str(e)}")

@bot.command(name='change')
async def change_account(ctx):
    """Change Gmail account"""
    global gmail_connector, email_agent, calendar_service, user_email, monitoring_active
    
    try:
        await ctx.send(f"🔄 Changing Gmail account...")
        
        # Stop monitoring
        monitoring_active = False
        if monitor_emails.is_running():
            monitor_emails.stop()
        
        # Remove old token to force re-authentication
        if os.path.exists('token.json'):
            os.remove('token.json')
            await ctx.send("🗑️ Removed old authentication")
        
        # Reset services
        gmail_connector = None
        email_agent = None
        calendar_service = None
        user_email = None
        
        await ctx.send("✅ Account cleared. Use `!setup` to authenticate with a different Gmail account.")
        
    except Exception as e:
        await ctx.send(f"❌ Error changing account: {str(e)}")

@bot.command(name='fix_calendar')
async def fix_calendar_permissions(ctx):
    """Fix calendar permission issues"""
    try:
        embed = discord.Embed(
            title="🔧 Fix Calendar Issues",
            description="If you're getting calendar errors, follow these steps:",
            color=0xffa500
        )
        
        embed.add_field(
            name="🎯 Step 1: Enable Calendar API",
            value="Go to your Google Cloud project and enable Calendar API\n[Direct Link](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)",
            inline=False
        )
        
        embed.add_field(
            name="🔄 Step 2: Reset Authentication",
            value="Use `!change` command to clear old permissions",
            inline=False
        )
        
        embed.add_field(
            name="🔑 Step 3: Re-authenticate",
            value="Use `!setup` command and grant ALL permissions when prompted",
            inline=False
        )
        
        embed.add_field(
            name="💡 Common Issues",
            value="• 'Unregistered callers' = Calendar API not enabled\n• 'Insufficient permissions' = Need to re-authenticate\n• 'Invalid scope' = Calendar API not enabled in project",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name='refresh')
async def refresh_emails(ctx):
    """Force check all unread emails (ignoring processed list)"""
    if not gmail_connector or not user_email:
        await ctx.send("❌ Please run `!setup` first.")
        return
    
    await ctx.send("🔄 Checking ALL unread emails (ignoring processed list)...")
    
    try:
        # Get all unread emails without checking processed list
        results = gmail_connector.service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            await ctx.send("📭 No unread emails found")
            return
        
        await ctx.send(f"📧 Found {len(messages)} unread emails. Processing...")
        
        for message in messages:
            message_id = message['id']
            
            # Get email data
            email_data = gmail_connector._get_email_data(message_id)
            
            if not email_data:
                continue
            
            # Process with AI
            analysis, reply = email_agent.process_email(email_data)
            classification = analysis.get('classification')
            confidence = analysis.get('confidence', 0) * 100
            
            # Create embed
            embed = discord.Embed(title="📧 Email Found", color=0x00ff00)
            embed.add_field(name="Subject", value=email_data.subject, inline=False)
            embed.add_field(name="From", value=f"{email_data.from_name} <{email_data.from_email}>", inline=False)
            embed.add_field(name="Date", value=email_data.date, inline=False)
            embed.add_field(name="Classification", value=f"{classification} ({confidence:.0f}%)", inline=True)
            
            # Handle meetings
            if classification == 'Meeting':
                embed.color = 0xff9900
                calendar_event = create_calendar_event(email_data, analysis)
                if calendar_event:
                    embed.add_field(name="Action", value="✅ Calendar event created", inline=False)
            
            await ctx.send(embed=embed)
            
            # Mark as processed
            processed_emails.add(message_id)
        
        save_processed_emails()
        
    except Exception as e:
        await ctx.send(f"❌ Error refreshing emails: {str(e)}")

@bot.command(name='test_calendar')
async def test_calendar(ctx):
    """Test calendar functionality with sample meeting"""
    if not calendar_service:
        await ctx.send("❌ Calendar service not available. Run `!setup` first.")
        return
    
    # Create test email data
    class TestEmailData:
        def __init__(self):
            self.message_id = "test_123"
            self.subject = "Team Sync Tomorrow"
            self.from_name = "Test User"
            self.from_email = "test@example.com"
            self.body = "Let's have a meeting tomorrow at 3 PM to discuss the project updates. It should take about 30 minutes."
    
    test_email = TestEmailData()
    test_analysis = {'classification': 'Meeting'}
    
    await ctx.send("🧪 Testing calendar functionality...")
    
    calendar_result = create_calendar_event(test_email, test_analysis)
    
    if calendar_result and calendar_result.get('success'):
        embed = discord.Embed(title="✅ Calendar Test Successful", color=0x00ff00)
        embed.add_field(name="Event Created", value=calendar_result.get('summary'), inline=False)
        embed.add_field(name="Time", value=f"{calendar_result.get('start_time')} - {calendar_result.get('end_time')}", inline=False)
        embed.add_field(name="Duration", value=f"{calendar_result.get('duration')} minutes", inline=True)
        
        if calendar_result.get('event_link'):
            embed.add_field(name="Link", value=f"[Open Event]({calendar_result['event_link']})", inline=False)
        
        await ctx.send(embed=embed)
    else:
        error_msg = calendar_result.get('error', 'Unknown error') if calendar_result else 'No result'
        await ctx.send(f"❌ Calendar test failed: {error_msg}")

@bot.command(name='clear')
async def clear_processed(ctx):
    """Clear processed emails (admin only)"""
    global processed_emails
    
    processed_emails.clear()
    save_processed_emails()
    
    await ctx.send("🗑️ Cleared all processed emails. Next check will process all unread emails.")

@bot.command(name='guide')
async def setup_guide(ctx):
    """Show complete setup guide"""
    embed = discord.Embed(
        title="🚀 ActionInbox Setup Guide",
        description="Get ActionInbox working in 3 minutes!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="🎯 The Problem",
        value="Google OAuth requires app verification. Users get 'access denied' errors.",
        inline=False
    )
    
    embed.add_field(
        name="✅ The Solution",
        value="Create your own FREE Google Cloud project. This bypasses all restrictions.",
        inline=False
    )
    
    embed.add_field(
        name="📋 Quick Steps",
        value="""1. Go to: https://console.cloud.google.com/
2. Create project: 'ActionInbox-YourName'
3. Enable Gmail API + Calendar API
4. Create OAuth credentials (Desktop app)
5. Download as 'credentials.json'
6. Use `!setup` command""",
        inline=False
    )
    
    embed.add_field(
        name="🔗 Direct Links",
        value="""[Create Project](https://console.cloud.google.com/projectcreate)
[Enable Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
[Enable Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
[Create Credentials](https://console.cloud.google.com/apis/credentials)""",
        inline=False
    )
    
    embed.add_field(
        name="💡 Why This Works",
        value="Each user becomes the 'developer' of their own project, giving full access without restrictions.",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='steps')
async def detailed_steps(ctx):
    """Show detailed setup steps"""
    embeds = []
    
    # Step 1
    embed1 = discord.Embed(
        title="📋 Step 1: Create Google Cloud Project",
        color=0x4285f4
    )
    embed1.add_field(
        name="Instructions",
        value="""1. Go to: https://console.cloud.google.com/
2. Click 'Select a project' → 'New Project'
3. Project name: `ActionInbox-YourName`
4. Click 'Create' and wait
5. Make sure your new project is selected""",
        inline=False
    )
    embed1.add_field(
        name="🔗 Direct Link",
        value="[Create Project](https://console.cloud.google.com/projectcreate)",
        inline=False
    )
    embeds.append(embed1)
    
    # Step 2
    embed2 = discord.Embed(
        title="📧 Step 2: Enable APIs",
        color=0xea4335
    )
    embed2.add_field(
        name="Instructions",
        value="""1. In Google Cloud Console, go to 'APIs & Services' → 'Library'
2. Search for 'Gmail API' and click 'Enable'
3. Search for 'Calendar API' and click 'Enable'
4. Wait for both APIs to be enabled""",
        inline=False
    )
    embed2.add_field(
        name="🔗 Direct Links",
        value="[Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)\n[Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)",
        inline=False
    )
    embeds.append(embed2)
    
    # Step 3
    embed3 = discord.Embed(
        title="🔑 Step 3: Create OAuth Credentials",
        color=0xfbbc04
    )
    embed3.add_field(
        name="Instructions",
        value="""1. Go to 'APIs & Services' → 'Credentials'
2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'
3. If prompted, configure OAuth consent screen:
   - User Type: External
   - App name: ActionInbox
   - Your email for support and developer contact
4. Application type: 'Desktop application'
5. Name: 'ActionInbox Desktop'
6. Click 'Create'
7. Download the JSON file
8. Rename it to 'credentials.json'
9. Keep it safe for the !setup command""",
        inline=False
    )
    embed3.add_field(
        name="🔗 Direct Link",
        value="[Create Credentials](https://console.cloud.google.com/apis/credentials)",
        inline=False
    )
    embeds.append(embed3)
    
    # Step 4
    embed4 = discord.Embed(
        title="🚀 Step 4: Use ActionInbox",
        color=0x34a853
    )
    embed4.add_field(
        name="Instructions",
        value="""1. Use `!setup` command in Discord
2. Follow the authentication flow
3. Grant all requested permissions
4. Use `!start` to begin monitoring
5. Enjoy automated email processing!""",
        inline=False
    )
    embed4.add_field(
        name="🎉 You're Done!",
        value="ActionInbox will now process your emails with AI and create calendar events automatically.",
        inline=False
    )
    embeds.append(embed4)
    
    for embed in embeds:
        await ctx.send(embed=embed)

@bot.command(name='links')
async def quick_links(ctx):
    """Show quick setup links"""
    embed = discord.Embed(
        title="🔗 Quick Setup Links",
        description="Click these links to set up your Google Cloud project:",
        color=0x0099ff
    )
    
    embed.add_field(
        name="1️⃣ Create Project",
        value="[Google Cloud Console](https://console.cloud.google.com/projectcreate)",
        inline=False
    )
    
    embed.add_field(
        name="2️⃣ Enable APIs",
        value="[Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)\n[Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)",
        inline=False
    )
    
    embed.add_field(
        name="3️⃣ Create Credentials",
        value="[OAuth Credentials](https://console.cloud.google.com/apis/credentials)",
        inline=False
    )
    
    embed.add_field(
        name="📋 Remember",
        value="""• Project name: `ActionInbox-YourName`
• Enable both Gmail API and Calendar API
• Credential type: Desktop application
• Download as: `credentials.json`
• Then use: `!setup` command""",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='commands')
async def commands_list(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🤖 ActionInbox Bot Commands",
        description="Complete command reference",
        color=0x0099ff
    )
    
    embed.add_field(
        name="🔧 Setup Commands",
        value="`!guide` - Complete setup guide\n`!steps` - Detailed step-by-step\n`!links` - Quick setup links\n`!setup` - Connect Gmail account\n`!change` - Change Gmail account",
        inline=False
    )
    
    embed.add_field(
        name="📧 Email Commands",
        value="`!start` - Start email monitoring\n`!stop` - Stop monitoring\n`!check` - Check emails now\n`!refresh` - Check ALL unread emails\n`!status` - Check service status",
        inline=False
    )
    
    embed.add_field(
        name="🧪 Testing Commands",
        value="`!test_calendar` - Test calendar\n`!fix_calendar` - Fix calendar permissions\n`!clear` - Clear processed emails",
        inline=False
    )
    
    embed.add_field(
        name="❓ Need Help?",
        value="Start with `!guide` for complete setup instructions",
        inline=False
    )
    
    await ctx.send(embed=embed)

def get_new_emails(max_results=10):
    """Get new unprocessed emails"""
    global processed_emails
    
    try:
        # Get unread emails
        results = gmail_connector.service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return []
        
        new_emails = []
        newly_processed = []
        
        print(f"\\nFound {len(messages)} unread emails")
        print(f"Already processed: {len(processed_emails)} emails")
        
        for message in messages:
            message_id = message['id']
            
            # Skip if already processed
            if message_id in processed_emails:
                print(f"SKIP: Already processed {message_id}")
                continue
            
            # Mark as processed immediately
            processed_emails.add(message_id)
            newly_processed.append(message_id)
            
            # Get email data
            email_data = gmail_connector._get_email_data(message_id)
            
            if not email_data:
                print(f"SKIP: Could not get data for {message_id}")
                continue
            
            # Check if recent (last 48 hours to catch more emails)
            try:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(email_data.date)
                
                if email_date and email_date <= (datetime.now() - timedelta(hours=48)):
                    print(f"SKIP: Old email - {email_data.subject}")
                    continue
            except:
                # If date parsing fails, include the email
                pass
            
            print(f"NEW: {email_data.subject} from {email_data.from_name}")
            new_emails.append(email_data)
        
        # Save processed emails
        if newly_processed:
            save_processed_emails()
            print(f"Marked {len(newly_processed)} emails as processed")
        
        return new_emails
        
    except Exception as e:
        print(f"Error getting emails: {e}")
        return []

@tasks.loop(seconds=60)
async def monitor_emails(channel):
    """Background monitoring task"""
    if not monitoring_active or not gmail_connector:
        return
    
    try:
        print(f"\\n[{datetime.now().strftime('%H:%M:%S')}] Checking for new emails...")
        
        new_emails = get_new_emails(max_results=5)
        
        if not new_emails:
            print("No new emails found")
            return
        
        print(f"Processing {len(new_emails)} new emails...")
        
        for email_data in new_emails:
            # Process with AI
            analysis, reply = email_agent.process_email(email_data)
            classification = analysis.get('classification')
            confidence = analysis.get('confidence', 0) * 100
            
            # Send notification with enhanced details
            embed = discord.Embed(title="📧 New Email Alert", color=0x00ff00)
            embed.add_field(name="Subject", value=email_data.subject, inline=False)
            embed.add_field(name="From", value=f"{email_data.from_name} <{email_data.from_email}>", inline=False)
            embed.add_field(name="Classification", value=f"{classification} ({confidence:.0f}%)", inline=True)
            
            # Add email preview
            preview = email_data.body[:100] + "..." if len(email_data.body) > 100 else email_data.body
            embed.add_field(name="Preview", value=preview, inline=False)
            
            # Handle meetings with enhanced calendar integration
            if classification == 'Meeting':
                embed.color = 0xff9900
                calendar_result = create_calendar_event(email_data, analysis)
                
                if calendar_result and calendar_result.get('success'):
                    embed.add_field(name="✅ Calendar Event Created", value=f"""
**Time:** {calendar_result.get('start_time', 'Unknown')}
**Duration:** {calendar_result.get('duration', 60)} minutes
**Location:** {calendar_result.get('location', 'Not specified')}
📧 Notification sent to organizer
""", inline=False)
                
                elif calendar_result and calendar_result.get('error'):
                    error_msg = str(calendar_result['error'])
                    if "unregistered callers" in error_msg or "API Key" in error_msg:
                        embed.add_field(name="⚠️ Calendar Setup Needed", value=f"""
📅 Meeting detected but Calendar API not enabled:
**Solution:** Use `!guide` and enable Calendar API in your Google Cloud project
**Quick Link:** [Enable Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
""", inline=False)
                    else:
                        embed.add_field(name="⚠️ Calendar Issue", value=f"""
📅 Meeting detected but calendar event failed:
**Error:** {error_msg}
**Fix:** Use `!fix_calendar` for troubleshooting
""", inline=False)
                else:
                    embed.add_field(name="Type", value="📅 Meeting detected (calendar not available)", inline=True)
            elif classification == 'Task':
                embed.color = 0xffa500
                embed.add_field(name="Type", value="📝 Task detected", inline=True)
            elif classification == 'Spam':
                embed.color = 0xff4444
                embed.add_field(name="Type", value="🚫 Spam detected", inline=True)
            
            embed.set_footer(text="ActionInbox Auto-Monitor")
            
            await channel.send(embed=embed)
        
    except Exception as e:
        print(f"Monitoring error: {e}")

def main():
    """Start the clean bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("❌ Discord bot token not found!")
        print("💡 Run 'python setup_wizard.py' to configure Discord bot")
        return
    
    print("Starting Clean ActionInbox Bot...")
    print("Fixed duplicate email processing")
    print("")
    print("🔧 Need help with OAuth errors?")
    print("   Run: python setup_wizard.py")
    print("   Or:  python quick_setup.py")
    print("")
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()