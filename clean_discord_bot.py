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

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Single service instance (one Gmail account)
gmail_connector = None
email_agent = None
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

@bot.event
async def on_ready():
    """Bot startup"""
    print(f'Clean ActionInbox Bot is online! Logged in as {bot.user}')
    load_processed_emails()
    print('Commands:')
    print('  !setup - Setup Gmail account')
    print('  !start - Start monitoring')
    print('  !stop - Stop monitoring')
    print('  !status - Check status')
    print('  !check - Check emails now')
    print('  !clear - Clear processed emails (admin)')

@bot.command(name='setup')
async def setup_gmail(ctx):
    """Setup Gmail account"""
    global gmail_connector, email_agent, user_email
    
    try:
        await ctx.send("🔧 Setting up Gmail account...")
        
        gmail_connector = GmailConnector()
        email_agent = ActionInbox()
        
        if not gmail_connector.authenticate():
            await ctx.send("❌ Gmail authentication failed!")
            return
        
        # Get user email
        profile = gmail_connector.service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress', 'Unknown')
        
        embed = discord.Embed(title="✅ Setup Complete", color=0x00ff00)
        embed.add_field(name="Gmail Account", value=user_email, inline=False)
        embed.add_field(name="Next Steps", value="Use `!start` to begin monitoring", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Setup error: {str(e)}")

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
            
            if classification == 'Meeting':
                embed.color = 0xff9900
                embed.add_field(name="Type", value="📅 Meeting detected", inline=True)
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error checking emails: {str(e)}")

@bot.command(name='clear')
async def clear_processed(ctx):
    """Clear processed emails (admin only)"""
    global processed_emails
    
    processed_emails.clear()
    save_processed_emails()
    
    await ctx.send("🗑️ Cleared all processed emails. Next check will process all unread emails.")

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
            
            # Check if recent (last 24 hours)
            try:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(email_data.date)
                
                if email_date and email_date <= (datetime.now() - timedelta(hours=24)):
                    print(f"SKIP: Old email - {email_data.subject}")
                    continue
            except:
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
        
    except Exception as e:
        print(f"Monitoring error: {e}")

def main():
    """Start the clean bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("❌ Discord bot token not found!")
        return
    
    print("Starting Clean ActionInbox Bot...")
    print("Fixed duplicate email processing")
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()