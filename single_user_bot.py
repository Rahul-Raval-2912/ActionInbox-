#!/usr/bin/env python3
"""
Single User ActionInbox Discord Bot
- Works with one Gmail account
- Multiple Discord users can view status
- Only owner can control the service
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

# Single service instance
gmail_connector = None
email_agent = None
calendar_service = None
monitoring_active = False
processed_emails = set()
user_email = None

# Owner Discord ID (replace with your Discord user ID)
OWNER_ID = 1409163505260826644  # Replace with your actual Discord user ID

def is_owner(user_id):
    """Check if user is the owner"""
    return user_id == OWNER_ID

@bot.event
async def on_ready():
    """Bot startup"""
    print(f'ActionInbox Single User Bot is online! Logged in as {bot.user}')
    print('Commands:')
    print('  !setup - Setup Gmail (owner only)')
    print('  !start - Start monitoring (owner only)')
    print('  !stop - Stop monitoring (owner only)')
    print('  !status - Check status (everyone)')
    print('  !check - Check emails now (owner only)')

@bot.command(name='setup')
async def setup_gmail(ctx):
    """Setup Gmail account (owner only)"""
    if not is_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can setup Gmail account.")
        return
    
    global gmail_connector, email_agent, calendar_service, user_email
    
    try:
        await ctx.send("🔧 Setting up Gmail account...")
        
        # Initialize services
        gmail_connector = GmailConnector()
        email_agent = ActionInbox()
        
        # Authenticate Gmail
        if not gmail_connector.authenticate():
            await ctx.send("❌ Gmail authentication failed!")
            return
        
        # Get user email
        profile = gmail_connector.service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress', 'Unknown')
        
        # Authenticate calendar
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json')
        
        if creds and creds.valid:
            calendar_service = build('calendar', 'v3', credentials=creds)
        
        embed = discord.Embed(title="✅ Setup Complete", color=0x00ff00)
        embed.add_field(name="Gmail Account", value=user_email, inline=False)
        embed.add_field(name="Calendar", value="✅ Connected" if calendar_service else "❌ Not available", inline=True)
        embed.add_field(name="Owner", value=ctx.author.mention, inline=True)
        embed.add_field(name="Next Steps", value="Use `!start` to begin monitoring", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Setup error: {str(e)}")

@bot.command(name='start')
async def start_monitoring(ctx):
    """Start email monitoring (owner only)"""
    if not is_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can start monitoring.")
        return
    
    global monitoring_active
    
    if not gmail_connector or not user_email:
        await ctx.send("❌ Please run `!setup` first.")
        return
    
    monitoring_active = True
    
    if not monitor_emails.is_running():
        monitor_emails.start(ctx.channel)
    
    embed = discord.Embed(title="🚀 Email Monitoring Started", color=0x00ff00)
    embed.add_field(name="Gmail Account", value=user_email, inline=False)
    embed.add_field(name="Started by", value=ctx.author.mention, inline=True)
    embed.add_field(name="Check Interval", value="60 seconds", inline=True)
    embed.add_field(name="Status", value="All server members can view notifications", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='stop')
async def stop_monitoring(ctx):
    """Stop email monitoring (owner only)"""
    if not is_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can stop monitoring.")
        return
    
    global monitoring_active
    
    monitoring_active = False
    if monitor_emails.is_running():
        monitor_emails.stop()
    
    await ctx.send(f"🛑 Email monitoring stopped by {ctx.author.mention}")

@bot.command(name='status')
async def check_status(ctx):
    """Check service status (everyone can view)"""
    embed = discord.Embed(title="📊 ActionInbox Status", color=0x0099ff)
    
    embed.add_field(name="Gmail Account", value=user_email or "Not configured", inline=False)
    embed.add_field(name="Monitoring", value="🟢 Active" if monitoring_active else "🔴 Stopped", inline=True)
    embed.add_field(name="Calendar", value="🟢 Connected" if calendar_service else "🔴 Not connected", inline=True)
    embed.add_field(name="Processed Emails", value=str(len(processed_emails)), inline=True)
    
    if is_owner(ctx.author.id):
        if monitoring_active:
            embed.add_field(name="Owner Commands", value="`!stop` - Stop monitoring\\n`!check` - Check emails now", inline=False)
        else:
            embed.add_field(name="Owner Commands", value="`!start` - Start monitoring\\n`!setup` - Reconfigure", inline=False)
    else:
        embed.add_field(name="Access", value="You can view status and notifications", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='check')
async def check_emails_now(ctx):
    """Check emails now (owner only)"""
    if not is_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can manually check emails.")
        return
    
    if not gmail_connector or not user_email:
        await ctx.send("❌ Please run `!setup` first.")
        return
    
    await ctx.send("🔍 Checking emails now...")
    
    try:
        # Get recent unread emails
        results = gmail_connector.service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=5
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            await ctx.send("📭 No unread emails found")
            return
        
        new_emails = []
        
        for message in messages:
            message_id = message['id']
            
            if message_id in processed_emails:
                continue
            
            processed_emails.add(message_id)
            
            email_data = gmail_connector._get_email_data(message_id)
            
            if email_data:
                # Only process recent emails (last 2 hours)
                from email.utils import parsedate_to_datetime
                try:
                    email_date = parsedate_to_datetime(email_data.date)
                    if email_date and email_date > (datetime.now() - timedelta(hours=2)):
                        new_emails.append(email_data)
                except:
                    pass
        
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
            
            # Handle meetings
            if classification == 'Meeting' and calendar_service:
                # Try to create calendar event
                embed.add_field(name="Action", value="📅 Calendar integration available", inline=True)
                embed.color = 0xff9900
            
            embed.set_footer(text=f"Processed by: {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error checking emails: {str(e)}")

@tasks.loop(seconds=60)
async def monitor_emails(channel):
    """Background monitoring task"""
    global processed_emails
    
    if not monitoring_active or not gmail_connector:
        return
    
    try:
        # Get recent unread emails
        results = gmail_connector.service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=3
        ).execute()
        
        messages = results.get('messages', [])
        
        for message in messages:
            message_id = message['id']
            
            if message_id in processed_emails:
                continue
            
            processed_emails.add(message_id)
            
            email_data = gmail_connector._get_email_data(message_id)
            
            if email_data:
                # Only process recent emails
                from email.utils import parsedate_to_datetime
                try:
                    email_date = parsedate_to_datetime(email_data.date)
                    if email_date and email_date > (datetime.now() - timedelta(hours=2)):
                        # Process with AI
                        analysis, reply = email_agent.process_email(email_data)
                        classification = analysis.get('classification')
                        confidence = analysis.get('confidence', 0) * 100
                        
                        # Send notification
                        embed = discord.Embed(title="📧 New Email Alert", color=0x00ff00)
                        embed.add_field(name="Subject", value=email_data.subject, inline=False)
                        embed.add_field(name="From", value=f"{email_data.from_name} <{email_data.from_email}>", inline=False)
                        embed.add_field(name="Classification", value=f"{classification} ({confidence:.0f}%)", inline=True)
                        
                        if classification == 'Meeting':
                            embed.color = 0xff9900
                            embed.add_field(name="Type", value="📅 Meeting detected", inline=True)
                        
                        embed.set_footer(text="ActionInbox Auto-Monitor")
                        
                        await channel.send(embed=embed)
                except:
                    pass
        
    except Exception as e:
        print(f"Monitoring error: {e}")

def main():
    """Start the single user bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("❌ Discord bot token not found!")
        return
    
    print("🤖 Starting Single User ActionInbox Bot...")
    print(f"🔒 Owner ID: {OWNER_ID}")
    print("📧 One Gmail account, multiple Discord viewers")
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()