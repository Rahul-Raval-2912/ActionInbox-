#!/usr/bin/env python3
"""
Complete ActionInbox Discord Bot
- All user management through Discord commands
- Multi-user support
- Email monitoring with 60-second intervals
- Account switching via bot commands
"""

import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import time
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

# Global service data
user_services = {}  # Store service instances per Discord user
processed_emails_file = 'processed_emails.json'

class UserEmailService:
    def __init__(self, discord_user_id):
        self.discord_user_id = discord_user_id
        self.gmail_connector = GmailConnector()
        self.email_agent = ActionInbox()
        self.calendar_service = None
        self.user_email = None
        self.processed_emails = self.load_processed_emails()
        self.monitoring_active = False
        
    def load_processed_emails(self):
        """Load processed emails for this user"""
        try:
            if os.path.exists(processed_emails_file):
                with open(processed_emails_file, 'r') as f:
                    all_data = json.load(f)
                    return set(all_data.get(str(self.discord_user_id), []))
            return set()
        except:
            return set()
    
    def save_processed_emails(self):
        """Save processed emails for this user"""
        try:
            all_data = {}
            if os.path.exists(processed_emails_file):
                with open(processed_emails_file, 'r') as f:
                    all_data = json.load(f)
            
            all_data[str(self.discord_user_id)] = list(self.processed_emails)
            
            with open(processed_emails_file, 'w') as f:
                json.dump(all_data, f)
        except Exception as e:
            print(f"Error saving processed emails: {e}")
    
    def authenticate_gmail(self):
        """Authenticate Gmail for this user"""
        try:
            # Use user-specific token file
            user_token_file = f'token_{self.discord_user_id}.json'
            
            if not self.gmail_connector.authenticate():
                return False, "Gmail authentication failed"
            
            # Get user email
            profile = self.gmail_connector.service.users().getProfile(userId='me').execute()
            self.user_email = profile.get('emailAddress', 'Unknown')
            
            # Authenticate calendar
            creds = None
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json')
            
            if creds and creds.valid:
                self.calendar_service = build('calendar', 'v3', credentials=creds)
            
            return True, f"Authenticated: {self.user_email}"
            
        except Exception as e:
            return False, f"Authentication error: {str(e)}"
    
    def get_new_emails(self, max_results=10):
        """Get unprocessed emails"""
        try:
            results = self.gmail_connector.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            new_emails = []
            
            for message in messages:
                message_id = message['id']
                
                if message_id in self.processed_emails:
                    continue
                
                email_data = self.gmail_connector._get_email_data(message_id)
                
                if email_data:
                    # Only process recent emails (last 24 hours)
                    email_date = self.parse_email_date(email_data.date)
                    if email_date and email_date > (datetime.now() - timedelta(hours=24)):
                        new_emails.append(email_data)
                        self.processed_emails.add(message_id)
            
            if new_emails:
                self.save_processed_emails()
            
            return new_emails
            
        except Exception as e:
            print(f"Error getting emails: {e}")
            return []
    
    def parse_email_date(self, date_string):
        """Parse email date"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_string)
        except:
            return None
    
    def create_calendar_event(self, email_data, analysis):
        """Create calendar event for meetings"""
        try:
            if analysis.get('classification') != 'Meeting' or not self.calendar_service:
                return False
            
            meeting_time = self.parse_meeting_time(email_data.body)
            if not meeting_time:
                return False
            
            event_details = {
                'summary': f"Meeting: {email_data.subject}",
                'description': f"Auto-created by ActionInbox\\n\\nFrom: {email_data.from_name} <{email_data.from_email}>\\n\\n{email_data.body[:300]}...",
                'start': {
                    'dateTime': meeting_time['start'],
                    'timeZone': 'Asia/Kolkata'
                },
                'end': {
                    'dateTime': meeting_time['end'],
                    'timeZone': 'Asia/Kolkata'
                },
                'attendees': [
                    {'email': email_data.from_email},
                    {'email': self.user_email}
                ]
            }
            
            event = self.calendar_service.events().insert(
                calendarId='primary',
                body=event_details,
                sendUpdates='all'
            ).execute()
            
            return event
            
        except Exception as e:
            print(f"Calendar error: {e}")
            return False
    
    def parse_meeting_time(self, body):
        """Parse meeting time from email"""
        import re
        
        try:
            body_lower = body.lower()
            
            time_patterns = [
                r'(\\d{1,2}):(\\d{2})\\s*(am|pm)',
                r'(\\d{1,2})\\s*(am|pm)',
                r'at\\s+(\\d{1,2}):(\\d{2})',
                r'(\\d{1,2}):(\\d{2})'
            ]
            
            meeting_hour = 14
            meeting_minute = 0
            
            for pattern in time_patterns:
                match = re.search(pattern, body_lower)
                if match:
                    groups = match.groups()
                    hour = int(groups[0])
                    minute = int(groups[1]) if len(groups) > 1 and groups[1].isdigit() else 0
                    ampm = groups[-1] if len(groups) > 2 else None
                    
                    if ampm and 'pm' in ampm and hour != 12:
                        hour += 12
                    elif ampm and 'am' in ampm and hour == 12:
                        hour = 0
                    
                    meeting_hour = hour
                    meeting_minute = minute
                    break
            
            meeting_date = datetime.now() + timedelta(days=1)
            
            if 'today' in body_lower:
                meeting_date = datetime.now()
            elif 'tomorrow' in body_lower:
                meeting_date = datetime.now() + timedelta(days=1)
            
            meeting_start = meeting_date.replace(
                hour=meeting_hour,
                minute=meeting_minute,
                second=0,
                microsecond=0
            )
            
            meeting_end = meeting_start + timedelta(hours=1)
            
            return {
                'start': meeting_start.isoformat(),
                'end': meeting_end.isoformat()
            }
            
        except:
            return None

@bot.event
async def on_ready():
    """Bot startup"""
    print(f'ActionInbox Complete Bot is online! Logged in as {bot.user}')
    print('Available commands:')
    print('  !setup - Setup your Gmail account')
    print('  !start - Start email monitoring')
    print('  !stop - Stop monitoring')
    print('  !status - Check your service status')
    print('  !change - Change Gmail account')
    print('  !check - Check emails now')

@bot.command(name='setup')
async def setup_account(ctx):
    """Setup Gmail account for user"""
    user_id = ctx.author.id
    
    try:
        await ctx.send(f"🔧 Setting up ActionInbox for {ctx.author.mention}...")
        
        # Create user service
        if user_id not in user_services:
            user_services[user_id] = UserEmailService(user_id)
        
        service = user_services[user_id]
        
        # Authenticate
        success, message = service.authenticate_gmail()
        
        if success:
            embed = discord.Embed(title="✅ Setup Complete", color=0x00ff00)
            embed.add_field(name="Gmail Account", value=service.user_email, inline=False)
            embed.add_field(name="Calendar", value="✅ Connected" if service.calendar_service else "❌ Not available", inline=True)
            embed.add_field(name="Next Steps", value="Use `!start` to begin monitoring emails", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Setup failed: {message}")
            
    except Exception as e:
        await ctx.send(f"❌ Setup error: {str(e)}")

@bot.command(name='start')
async def start_monitoring(ctx):
    """Start email monitoring for user"""
    user_id = ctx.author.id
    
    if user_id not in user_services:
        await ctx.send("❌ Please run `!setup` first to configure your Gmail account.")
        return
    
    service = user_services[user_id]
    
    if not service.user_email:
        await ctx.send("❌ Gmail not authenticated. Run `!setup` first.")
        return
    
    service.monitoring_active = True
    
    # Start monitoring task for this user
    if not monitor_user_emails.is_running():
        monitor_user_emails.start()
    
    embed = discord.Embed(title="🚀 Email Monitoring Started", color=0x00ff00)
    embed.add_field(name="User", value=ctx.author.mention, inline=True)
    embed.add_field(name="Gmail Account", value=service.user_email, inline=True)
    embed.add_field(name="Check Interval", value="60 seconds", inline=True)
    embed.add_field(name="Features", value="✅ AI Classification\\n✅ Calendar Events\\n✅ Smart Replies", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='stop')
async def stop_monitoring(ctx):
    """Stop email monitoring for user"""
    user_id = ctx.author.id
    
    if user_id in user_services:
        user_services[user_id].monitoring_active = False
        await ctx.send(f"🛑 Email monitoring stopped for {ctx.author.mention}")
    else:
        await ctx.send("❌ No active monitoring found for your account.")

@bot.command(name='status')
async def check_status(ctx):
    """Check user's service status"""
    user_id = ctx.author.id
    
    embed = discord.Embed(title=f"📊 Status for {ctx.author.display_name}", color=0x0099ff)
    
    if user_id in user_services:
        service = user_services[user_id]
        
        embed.add_field(name="Gmail Account", value=service.user_email or "Not configured", inline=False)
        embed.add_field(name="Monitoring", value="🟢 Active" if service.monitoring_active else "🔴 Stopped", inline=True)
        embed.add_field(name="Calendar", value="🟢 Connected" if service.calendar_service else "🔴 Not connected", inline=True)
        embed.add_field(name="Processed Emails", value=str(len(service.processed_emails)), inline=True)
        
        if service.monitoring_active:
            embed.add_field(name="Available Commands", value="`!stop` - Stop monitoring\\n`!check` - Check emails now\\n`!change` - Change account", inline=False)
        else:
            embed.add_field(name="Available Commands", value="`!start` - Start monitoring\\n`!change` - Change account", inline=False)
    else:
        embed.add_field(name="Status", value="Not configured", inline=False)
        embed.add_field(name="Setup", value="Run `!setup` to get started", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='change')
async def change_account(ctx):
    """Change Gmail account"""
    user_id = ctx.author.id
    
    await ctx.send(f"🔄 Changing Gmail account for {ctx.author.mention}...")
    
    # Stop current monitoring
    if user_id in user_services:
        user_services[user_id].monitoring_active = False
    
    # Remove old token
    if os.path.exists('token.json'):
        os.remove('token.json')
    
    # Setup new account
    await setup_account(ctx)

@bot.command(name='check')
async def check_emails_now(ctx):
    """Manually check emails now"""
    user_id = ctx.author.id
    
    if user_id not in user_services:
        await ctx.send("❌ Please run `!setup` first.")
        return
    
    service = user_services[user_id]
    
    if not service.user_email:
        await ctx.send("❌ Gmail not authenticated. Run `!setup` first.")
        return
    
    await ctx.send("🔍 Checking emails now...")
    
    try:
        new_emails = service.get_new_emails(max_results=5)
        
        if not new_emails:
            await ctx.send("📭 No new emails to process")
            return
        
        await ctx.send(f"📧 Processing {len(new_emails)} new emails...")
        
        for email_data in new_emails:
            # Process with AI
            analysis, reply = service.email_agent.process_email(email_data)
            classification = analysis.get('classification')
            confidence = analysis.get('confidence', 0) * 100
            
            # Create embed for each email
            embed = discord.Embed(title="📧 Email Processed", color=0x00ff00)
            embed.add_field(name="Subject", value=email_data.subject, inline=False)
            embed.add_field(name="From", value=f"{email_data.from_name} <{email_data.from_email}>", inline=False)
            embed.add_field(name="Classification", value=classification, inline=True)
            embed.add_field(name="Confidence", value=f"{confidence:.0f}%", inline=True)
            
            # Handle meetings
            if classification == 'Meeting':
                calendar_event = service.create_calendar_event(email_data, analysis)
                if calendar_event:
                    embed.add_field(name="Action", value="✅ Calendar event created & notification sent", inline=False)
                    embed.color = 0xff9900
            
            # Add suggested reply
            if classification == 'Meeting':
                reply_text = "Thank you for the meeting invitation. I've added it to my calendar."
            elif classification == 'Task':
                reply_text = "I've received your request and will review it promptly."
            elif classification == 'Invoice':
                reply_text = "Thank you for the invoice. I'll process it according to our terms."
            else:
                reply_text = "Thank you for your email. I've received and noted the information."
            
            embed.add_field(name="💬 Suggested Reply", value=reply_text, inline=False)
            embed.set_footer(text=f"For: {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error checking emails: {str(e)}")

@tasks.loop(seconds=60)
async def monitor_user_emails():
    """Background task to monitor emails for all active users"""
    for user_id, service in user_services.items():
        if not service.monitoring_active or not service.user_email:
            continue
        
        try:
            new_emails = service.get_new_emails(max_results=3)
            
            if new_emails:
                # Get Discord channel to send notifications
                channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
                channel = bot.get_channel(channel_id)
                
                if channel:
                    user = bot.get_user(user_id)
                    
                    for email_data in new_emails:
                        # Process email
                        analysis, reply = service.email_agent.process_email(email_data)
                        classification = analysis.get('classification')
                        confidence = analysis.get('confidence', 0) * 100
                        
                        # Create notification embed
                        embed = discord.Embed(title="📧 New Email Alert", color=0x00ff00)
                        embed.add_field(name="User", value=user.mention if user else f"User {user_id}", inline=True)
                        embed.add_field(name="Subject", value=email_data.subject, inline=False)
                        embed.add_field(name="From", value=f"{email_data.from_name} <{email_data.from_email}>", inline=False)
                        embed.add_field(name="Classification", value=f"{classification} ({confidence:.0f}%)", inline=True)
                        
                        # Handle meetings
                        if classification == 'Meeting':
                            calendar_event = service.create_calendar_event(email_data, analysis)
                            if calendar_event:
                                embed.add_field(name="Action", value="✅ Calendar event created", inline=True)
                                embed.color = 0xff9900
                        
                        embed.set_footer(text="ActionInbox Auto-Monitor")
                        
                        await channel.send(embed=embed)
        
        except Exception as e:
            print(f"Monitoring error for user {user_id}: {e}")

def main():
    """Start the complete Discord bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("❌ Discord bot token not found!")
        return
    
    print("🤖 Starting Complete ActionInbox Discord Bot...")
    print("🔗 Multi-user email monitoring with full Discord control")
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()