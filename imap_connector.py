#!/usr/bin/env python3
"""
IMAP Email Connector - Alternative to Gmail API
Works with any email provider without OAuth restrictions
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime
import ssl

class IMAPConnector:
    def __init__(self):
        self.connection = None
        self.email_address = None
    
    def connect(self, email_address, password, imap_server="imap.gmail.com", port=993):
        """Connect to email account via IMAP"""
        try:
            self.email_address = email_address
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to server
            self.connection = imaplib.IMAP4_SSL(imap_server, port, ssl_context=context)
            
            # Login
            self.connection.login(email_address, password)
            
            print(f"✅ Connected to {email_address}")
            return True
            
        except Exception as e:
            print(f"❌ IMAP connection failed: {e}")
            return False
    
    def get_unread_emails(self, max_results=10):
        """Get unread emails via IMAP"""
        try:
            if not self.connection:
                return []
            
            # Select inbox
            self.connection.select('INBOX')
            
            # Search for unread emails
            status, messages = self.connection.search(None, 'UNSEEN')
            
            if status != 'OK':
                return []
            
            email_ids = messages[0].split()
            
            # Limit results
            email_ids = email_ids[-max_results:] if len(email_ids) > max_results else email_ids
            
            emails = []
            
            for email_id in email_ids:
                # Fetch email
                status, msg_data = self.connection.fetch(email_id, '(RFC822)')
                
                if status != 'OK':
                    continue
                
                # Parse email
                email_message = email.message_from_bytes(msg_data[0][1])
                
                # Extract email data
                email_data = self.parse_email(email_message, email_id.decode())
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            print(f"❌ Error getting emails: {e}")
            return []
    
    def parse_email(self, email_message, email_id):
        """Parse email message into structured data"""
        try:
            # Get subject
            subject = self.decode_header_value(email_message.get('Subject', ''))
            
            # Get sender
            from_header = email_message.get('From', '')
            from_name, from_email = self.parse_from_header(from_header)
            
            # Get recipient
            to_email = email_message.get('To', '')
            
            # Get date
            date = email_message.get('Date', '')
            
            # Get body
            body = self.extract_body(email_message)
            
            # Create email data object
            class EmailData:
                def __init__(self):
                    self.message_id = email_id
                    self.subject = subject
                    self.from_name = from_name
                    self.from_email = from_email
                    self.to_email = to_email
                    self.date = date
                    self.body = body
                    self.cc_emails = ""
                    self.attachments = []
                    self.recipient_timezone = "UTC"
                    self.message_link = None
            
            return EmailData()
            
        except Exception as e:
            print(f"❌ Error parsing email: {e}")
            return None
    
    def decode_header_value(self, header_value):
        """Decode email header value"""
        try:
            if not header_value:
                return ""
            
            decoded_parts = decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string.strip()
            
        except Exception as e:
            return str(header_value)
    
    def parse_from_header(self, from_header):
        """Parse From header to get name and email"""
        try:
            decoded_from = self.decode_header_value(from_header)
            
            if '<' in decoded_from and '>' in decoded_from:
                # Format: "Name <email@domain.com>"
                name_part = decoded_from.split('<')[0].strip().strip('"')
                email_part = decoded_from.split('<')[1].split('>')[0].strip()
                return name_part, email_part
            else:
                # Just email address
                return decoded_from, decoded_from
                
        except Exception as e:
            return from_header, from_header
    
    def extract_body(self, email_message):
        """Extract email body text"""
        try:
            body = ""
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        charset = part.get_content_charset() or 'utf-8'
                        body_bytes = part.get_payload(decode=True)
                        if body_bytes:
                            body += body_bytes.decode(charset, errors='ignore')
            else:
                charset = email_message.get_content_charset() or 'utf-8'
                body_bytes = email_message.get_payload(decode=True)
                if body_bytes:
                    body = body_bytes.decode(charset, errors='ignore')
            
            return body.strip()
            
        except Exception as e:
            return f"Error extracting body: {e}"
    
    def close(self):
        """Close IMAP connection"""
        try:
            if self.connection:
                self.connection.close()
                self.connection.logout()
        except:
            pass

# Test function
def test_imap():
    """Test IMAP connection"""
    connector = IMAPConnector()
    
    # Test with Gmail (requires app password)
    email_addr = input("Enter Gmail address: ")
    password = input("Enter app password: ")
    
    if connector.connect(email_addr, password):
        emails = connector.get_unread_emails(3)
        
        print(f"\nFound {len(emails)} unread emails:")
        for email_data in emails:
            print(f"- {email_data.subject} (from: {email_data.from_name})")
        
        connector.close()

if __name__ == "__main__":
    test_imap()