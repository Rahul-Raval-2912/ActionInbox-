import base64
import json
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os
from action_inbox import ActionInbox, EmailData

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.send']

class GmailConnector:
    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.agent = ActionInbox()
        
    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    
    def get_unread_emails(self, max_results=10):
        """Get unread emails from inbox"""
        try:
            results = self.service.users().messages().list(
                userId='me', q='is:unread', maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                email_data = self._get_email_data(message['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def _get_email_data(self, message_id):
        """Convert Gmail message to EmailData object"""
        try:
            message = self.service.users().messages().get(userId='me', id=message_id).execute()
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            # Extract body
            body = self._extract_body(message['payload'])
            
            # Extract attachments
            attachments = self._extract_attachments(message['payload'])
            
            return EmailData(
                message_id=message_id,
                subject=headers.get('Subject', ''),
                from_name=self._extract_name(headers.get('From', '')),
                from_email=self._extract_email(headers.get('From', '')),
                to_email=headers.get('To', ''),
                cc_emails=headers.get('Cc', ''),
                date=headers.get('Date', ''),
                recipient_timezone=None,  # Could be extracted from user settings
                message_link=f"https://mail.google.com/mail/u/0/#inbox/{message_id}",
                body=body,
                attachments=attachments
            )
        except Exception as e:
            print(f"Error processing message {message_id}: {e}")
            return None
    
    def _extract_body(self, payload):
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        elif payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def _extract_attachments(self, payload):
        """Extract attachment info from payload"""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):
                    attachments.append({
                        'filename': part['filename'],
                        'mime': part['mimeType'],
                        'text': None  # Would need separate API call to get content
                    })
        
        return attachments
    
    def _extract_name(self, from_field):
        """Extract name from From field"""
        if '<' in from_field:
            return from_field.split('<')[0].strip().strip('"')
        return from_field
    
    def _extract_email(self, from_field):
        """Extract email from From field"""
        if '<' in from_field:
            return from_field.split('<')[1].strip('>')
        return from_field
    
    def process_emails(self):
        """Process unread emails and return results"""
        emails = self.get_unread_emails()
        results = []
        
        for email_data in emails:
            analysis, reply = self.agent.process_email(email_data)
            results.append({
                'email_id': email_data.message_id,
                'analysis': analysis,
                'reply': reply
            })
        
        return results
    
    def send_reply(self, to_email, subject, body):
        """Send reply email"""
        try:
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error sending reply: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    connector = GmailConnector()
    if connector.authenticate():
        results = connector.process_emails()
        for result in results:
            print(f"Email: {result['analysis']['summary']}")
            print(f"Actions: {result['analysis']['next_actions']}")
            print("---")