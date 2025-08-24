#!/usr/bin/env python3
"""
Multi-Account ActionInbox Bot using IMAP
- No OAuth restrictions
- Multiple Gmail accounts
- Uses app passwords instead of OAuth
"""

import discord
from discord.ext import commands, tasks
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from imap_connector import IMAPConnector
from action_inbox import ActionInbox

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Store multiple email accounts
email_accounts = {}  # {discord_user_id: {'connector': IMAPConnector, 'email': str, 'monitoring': bool}}
email_agent = ActionInbox()

@bot.event
async def on_ready():
    """Bot startup"""
    print(f'Multi-Account ActionInbox Bot is online! Logged in as {bot.user}')
    print('Commands:')
    print('  !add_email - Add your email account')
    print('  !start - Start monitoring your emails')
    print('  !stop - Stop monitoring')
    print('  !status - Check your accounts')
    print('  !list_accounts - Show all connected accounts')

@bot.command(name='add_email')
async def add_email_account(ctx):
    """Add email account using IMAP"""
    user_id = ctx.author.id
    
    await ctx.send(f"📧 Setting up email account for {ctx.author.mention}")
    await ctx.send("**Step 1:** Enable 2-Factor Authentication on your Gmail")
    await ctx.send("**Step 2:** Generate App Password: https://myaccount.google.com/apppasswords")
    await ctx.send("**Step 3:** Reply with your email and app password in format:")
    await ctx.send("```email@gmail.com your_app_password_here```")
    
    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel
    
    try:
        # Wait for user response
        response = await bot.wait_for('message', check=check, timeout=300)  # 5 minutes
        
        parts = response.content.strip().split()
        if len(parts) != 2:
            await ctx.send("❌ Invalid format. Use: `email@gmail.com your_app_password`")
            return
        
        email_address, app_password = parts
        
        # Test connection
        await ctx.send("🔄 Testing connection...")
        
        connector = IMAPConnector()
        if connector.connect(email_address, app_password):
            # Store account
            email_accounts[user_id] = {
                'connector': connector,
                'email': email_address,
                'monitoring': False,
                'processed_emails': set()
            }
            
            embed = discord.Embed(title="✅ Email Account Added", color=0x00ff00)
            embed.add_field(name="Email", value=email_address, inline=False)
            embed.add_field(name="User", value=ctx.author.mention, inline=True)
            embed.add_field(name="Status", value="Ready to monitor", inline=True)
            embed.add_field(name="Next Step", value="Use `!start` to begin monitoring", inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Connection failed. Check your email and app password.")
    
    except Exception as e:
        await ctx.send(f"❌ Setup failed: {str(e)}")

@bot.command(name='start')
async def start_monitoring(ctx):
    """Start monitoring user's email"""
    user_id = ctx.author.id
    
    if user_id not in email_accounts:
        await ctx.send("❌ Please add your email account first using `!add_email`")
        return
    
    email_accounts[user_id]['monitoring'] = True
    
    # Start monitoring task if not running
    if not monitor_all_emails.is_running():
        monitor_all_emails.start()
    
    embed = discord.Embed(title="🚀 Email Monitoring Started", color=0x00ff00)
    embed.add_field(name="Email", value=email_accounts[user_id]['email'], inline=False)
    embed.add_field(name="User", value=ctx.author.mention, inline=True)
    embed.add_field(name="Check Interval", value="60 seconds", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='stop')
async def stop_monitoring(ctx):
    """Stop monitoring user's email"""
    user_id = ctx.author.id
    
    if user_id in email_accounts:
        email_accounts[user_id]['monitoring'] = False
        await ctx.send(f"🛑 Email monitoring stopped for {ctx.author.mention}")
    else:
        await ctx.send("❌ No email account found for your user.")

@bot.command(name='status')
async def check_status(ctx):
    """Check user's email status"""
    user_id = ctx.author.id
    
    embed = discord.Embed(title=f"📊 Status for {ctx.author.display_name}", color=0x0099ff)
    
    if user_id in email_accounts:
        account = email_accounts[user_id]
        
        embed.add_field(name="Email Account", value=account['email'], inline=False)
        embed.add_field(name="Monitoring", value="🟢 Active" if account['monitoring'] else "🔴 Stopped", inline=True)
        embed.add_field(name="Processed Emails", value=str(len(account['processed_emails'])), inline=True)
        
        if account['monitoring']:
            embed.add_field(name="Commands", value="`!stop` - Stop monitoring", inline=False)
        else:
            embed.add_field(name="Commands", value="`!start` - Start monitoring", inline=False)
    else:
        embed.add_field(name="Status", value="No email account configured", inline=False)
        embed.add_field(name="Setup", value="Use `!add_email` to get started", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='list_accounts')
async def list_all_accounts(ctx):
    """List all connected email accounts"""
    if not email_accounts:
        await ctx.send("📭 No email accounts connected yet.")
        return
    
    embed = discord.Embed(title="📧 Connected Email Accounts", color=0x0099ff)
    
    for user_id, account in email_accounts.items():
        user = bot.get_user(user_id)
        user_name = user.display_name if user else f"User {user_id}"
        
        status = "🟢 Monitoring" if account['monitoring'] else "🔴 Stopped"
        embed.add_field(
            name=f"{user_name}",
            value=f"📧 {account['email']}\\n{status}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='check')
async def check_emails_now(ctx):
    """Manually check emails for user"""
    user_id = ctx.author.id
    
    if user_id not in email_accounts:
        await ctx.send("❌ Please add your email account first using `!add_email`")
        return
    
    account = email_accounts[user_id]
    
    await ctx.send("🔍 Checking your emails now...")
    
    try:
        # Get unread emails
        emails = account['connector'].get_unread_emails(5)
        
        if not emails:
            await ctx.send("📭 No unread emails found")
            return
        
        new_emails = []
        
        for email_data in emails:
            email_id = email_data.message_id
            
            if email_id in account['processed_emails']:
                continue
            
            account['processed_emails'].add(email_id)
            new_emails.append(email_data)
        
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
            embed.add_field(name="Account", value=account['email'], inline=True)
            embed.add_field(name="Subject", value=email_data.subject, inline=False)
            embed.add_field(name="From", value=f"{email_data.from_name} <{email_data.from_email}>", inline=False)
            embed.add_field(name="Classification", value=f"{classification} ({confidence:.0f}%)", inline=True)
            
            if classification == 'Meeting':
                embed.color = 0xff9900
                embed.add_field(name="Type", value="📅 Meeting detected", inline=True)
            
            embed.set_footer(text=f"For: {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error checking emails: {str(e)}")

@tasks.loop(seconds=60)
async def monitor_all_emails():
    """Monitor all active email accounts"""
    channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
    channel = bot.get_channel(channel_id)
    
    if not channel:
        return
    
    for user_id, account in email_accounts.items():
        if not account['monitoring']:
            continue
        
        try:
            # Get unread emails
            emails = account['connector'].get_unread_emails(3)
            
            for email_data in emails:
                email_id = email_data.message_id
                
                if email_id in account['processed_emails']:
                    continue
                
                account['processed_emails'].add(email_id)
                
                # Process with AI
                analysis, reply = email_agent.process_email(email_data)
                classification = analysis.get('classification')
                confidence = analysis.get('confidence', 0) * 100
                
                # Get user
                user = bot.get_user(user_id)
                user_name = user.display_name if user else f"User {user_id}"
                
                # Send notification
                embed = discord.Embed(title="📧 New Email Alert", color=0x00ff00)
                embed.add_field(name="Account", value=f"{account['email']} ({user_name})", inline=False)
                embed.add_field(name="Subject", value=email_data.subject, inline=False)
                embed.add_field(name="From", value=f"{email_data.from_name} <{email_data.from_email}>", inline=False)
                embed.add_field(name="Classification", value=f"{classification} ({confidence:.0f}%)", inline=True)
                
                if classification == 'Meeting':
                    embed.color = 0xff9900
                    embed.add_field(name="Type", value="📅 Meeting detected", inline=True)
                
                embed.set_footer(text="ActionInbox Multi-Account Monitor")
                
                await channel.send(embed=embed)
        
        except Exception as e:
            print(f"Monitoring error for {account['email']}: {e}")

def main():
    """Start the multi-account bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("❌ Discord bot token not found!")
        return
    
    print("🤖 Starting Multi-Account ActionInbox Bot...")
    print("📧 Supports multiple Gmail accounts via IMAP")
    print("🔑 Uses app passwords (no OAuth restrictions)")
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()