import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class EmailData:
    message_id: str
    subject: str
    from_name: str
    from_email: str
    to_email: str
    cc_emails: str
    date: str
    recipient_timezone: Optional[str]
    message_link: Optional[str]
    body: str
    attachments: List[Dict[str, Any]]

class ActionInbox:
    def __init__(self):
        self.classification_keywords = {
            'Task': ['please', 'need', 'request', 'deliver', 'complete', 'approve', 'review', 'action required'],
            'Meeting': ['meeting', 'call', 'sync', 'schedule', 'calendar', 'invite', 'zoom', 'teams', 'discuss', 'chat', 'talk'],
            'Invoice': ['invoice', 'bill', 'payment', 'receipt', 'amount', 'total', 'due', 'vendor'],
            'Spam': ['unsubscribe', 'marketing', 'promotion', 'offer', 'deal', 'click here'],
            'FYI': ['fyi', 'information', 'update', 'notice', 'announcement']
        }

    def process_email(self, email_data: EmailData) -> tuple[Dict, Dict]:
        """Process email and return analysis and reply JSON objects"""
        
        # Classify email
        classification, confidence = self._classify_email(email_data)
        
        # Extract entities
        entities = self._extract_entities(email_data, classification)
        
        # Determine actions
        next_actions, labels = self._determine_actions(classification, email_data)
        
        # Check if needs review
        needs_review = confidence < 0.60 or self._has_opt_out(email_data.body)
        
        # Generate summary
        summary = self._generate_summary(email_data, classification)
        
        # Create analysis JSON
        analysis = {
            "classification": classification,
            "confidence": confidence,
            "needs_review": needs_review,
            "summary": summary,
            "entities": entities,
            "next_actions": next_actions,
            "labels": labels,
            "reason": self._generate_reason(classification, entities)
        }
        
        # Create reply JSON
        reply = self._generate_reply(email_data, classification, entities)
        
        return analysis, reply

    def _classify_email(self, email_data: EmailData) -> tuple[str, float]:
        """Enhanced email classification with better logic"""
        subject = email_data.subject.lower()
        body = email_data.body.lower()
        from_email = email_data.from_email.lower()
        text = f"{subject} {body}"
        
        # Enhanced scoring system
        scores = {
            'Meeting': 0,
            'Task': 0,
            'Invoice': 0,
            'Spam': 0,
            'FYI': 0
        }
        
        # Enhanced Meeting Detection
        meeting_patterns = {
            'high': ['meeting at', 'call at', 'zoom at', 'teams meeting', 'scheduled for'],
            'medium': ['meeting', 'call', 'sync', 'discussion', 'appointment'],
            'low': ['catch up', 'demo', 'presentation', 'review']
        }
        
        time_patterns = {
            'high': [r'\d{1,2}:\d{2}\s*(am|pm)', r'tomorrow at \d', r'today at \d'],
            'medium': [r'\d{1,2}\s*(am|pm)', 'tomorrow', 'today', 'next week'],
            'low': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        }
        
        # Score meeting patterns
        for weight, patterns in meeting_patterns.items():
            multiplier = {'high': 30, 'medium': 20, 'low': 10}[weight]
            for pattern in patterns:
                if pattern in text:
                    scores['Meeting'] += multiplier
        
        # Score time patterns with regex
        for weight, patterns in time_patterns.items():
            multiplier = {'high': 25, 'medium': 15, 'low': 8}[weight]
            for pattern in patterns:
                if isinstance(pattern, str):
                    if pattern in text:
                        scores['Meeting'] += multiplier
                else:  # regex pattern
                    if re.search(pattern, text):
                        scores['Meeting'] += multiplier
        
        # Enhanced Task Detection
        task_patterns = {
            'high': ['please review', 'need approval', 'action required', 'urgent request'],
            'medium': ['please', 'need', 'request', 'approve', 'complete'],
            'low': ['update', 'send', 'provide', 'finish']
        }
        
        for weight, patterns in task_patterns.items():
            multiplier = {'high': 35, 'medium': 20, 'low': 12}[weight]
            for pattern in patterns:
                if pattern in text:
                    scores['Task'] += multiplier
        
        # Enhanced Spam Detection
        spam_indicators = {
            'high': ['click here to claim', 'you have won', 'congratulations winner'],
            'medium': ['unsubscribe', 'marketing', 'promotion', 'offer'],
            'low': ['deal', 'discount', 'free']
        }
        
        for weight, indicators in spam_indicators.items():
            multiplier = {'high': 40, 'medium': 25, 'low': 15}[weight]
            for indicator in indicators:
                if indicator in text:
                    scores['Spam'] += multiplier
        
        # Social media spam detection
        if any(x in from_email for x in ['linkedin', 'facebook', 'twitter']):
            if any(x in subject for x in ['invitation', 'connection']):
                scores['Spam'] += 35
        
        # Invoice Detection
        invoice_patterns = ['invoice #', 'payment due', 'amount due', 'bill', '$']
        for pattern in invoice_patterns:
            if pattern in text:
                scores['Invoice'] += 20
        
        # Get best classification
        max_score = max(scores.values())
        
        if max_score == 0:
            return 'FYI', 0.6
        
        classification = max(scores, key=scores.get)
        
        # Better confidence calculation
        total_score = sum(scores.values())
        confidence = min((max_score / max(total_score, 1)) * 0.85 + 0.15, 0.98)
        
        return classification, confidence

    def _extract_entities(self, email_data: EmailData, classification: str) -> Dict:
        """Extract structured entities based on classification"""
        entities = {
            "task_title": None,
            "task_details": None,
            "due_date": None,
            "meeting_start": None,
            "meeting_end": None,
            "timezone": email_data.recipient_timezone,
            "attendees": [],
            "location": None,
            "invoice_total": None,
            "currency": None,
            "vendor": None,
            "po_number": None,
            "attachments_of_interest": []
        }
        
        if classification == 'Task':
            entities["task_title"] = self._extract_task_title(email_data)
            entities["task_details"] = email_data.body[:200] + "..." if len(email_data.body) > 200 else email_data.body
            entities["due_date"] = self._extract_due_date(email_data.body)
            
        elif classification == 'Meeting':
            meeting_times = self._extract_meeting_times(email_data)
            entities.update(meeting_times)
            entities["attendees"] = [email_data.from_email]
            entities["location"] = self._extract_location(email_data.body)
            
        elif classification == 'Invoice':
            invoice_data = self._extract_invoice_data(email_data)
            entities.update(invoice_data)
            entities["attachments_of_interest"] = self._get_invoice_attachments(email_data.attachments)
            
        return entities

    def _extract_task_title(self, email_data: EmailData) -> Optional[str]:
        """Extract task title from subject or body"""
        # Clean subject line
        subject = re.sub(r'^(re:|fwd?:)\s*', '', email_data.subject, flags=re.IGNORECASE).strip()
        if subject and len(subject) < 100:
            return subject
        
        # Look for imperative sentences in body
        sentences = email_data.body.split('.')[:3]  # First 3 sentences
        for sentence in sentences:
            sentence = sentence.strip()
            if any(word in sentence.lower() for word in ['please', 'need', 'request', 'can you']):
                return sentence[:80] + "..." if len(sentence) > 80 else sentence
        
        return None

    def _extract_due_date(self, body: str) -> Optional[str]:
        """Extract due date in ISO format"""
        # Look for explicit date patterns
        date_patterns = [
            r'by (\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'due (\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'before (\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Simple date parsing - would need more robust implementation
                    return self._parse_date_string(date_str)
                except:
                    continue
        
        return None

    def _extract_meeting_times(self, email_data: EmailData) -> Dict:
        """Extract meeting start/end times"""
        body = email_data.body.lower()
        
        # Look for time patterns
        time_pattern = r'(\d{1,2}):(\d{2})\s*(am|pm)?'
        times = re.findall(time_pattern, body)
        
        if len(times) >= 2:
            # Assume first two times are start and end
            start_time = self._format_meeting_time(times[0], email_data)
            end_time = self._format_meeting_time(times[1], email_data)
            return {"meeting_start": start_time, "meeting_end": end_time}
        elif len(times) == 1:
            start_time = self._format_meeting_time(times[0], email_data)
            # Assume 30 min meeting
            return {"meeting_start": start_time, "meeting_end": None}
        
        return {"meeting_start": None, "meeting_end": None}

    def _extract_location(self, body: str) -> Optional[str]:
        """Extract meeting location"""
        location_keywords = ['zoom', 'teams', 'meet', 'room', 'office', 'location']
        for keyword in location_keywords:
            if keyword in body.lower():
                # Extract sentence containing location keyword
                sentences = body.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        return sentence.strip()[:50]
        return None

    def _extract_invoice_data(self, email_data: EmailData) -> Dict:
        """Extract invoice-related data"""
        # Check attachments first
        for attachment in email_data.attachments:
            if attachment.get('text'):
                invoice_data = self._parse_invoice_text(attachment['text'])
                if invoice_data['invoice_total']:
                    return invoice_data
        
        # Fall back to email body
        return self._parse_invoice_text(email_data.body)

    def _parse_invoice_text(self, text: str) -> Dict:
        """Parse invoice data from text"""
        # Look for currency and amounts
        amount_pattern = r'(?:total|amount|due|balance)[\s:]*([₹$€£]?)[\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)'
        match = re.search(amount_pattern, text, re.IGNORECASE)
        
        invoice_total = None
        currency = None
        
        if match:
            currency_symbol = match.group(1)
            amount_str = match.group(2).replace(',', '')
            try:
                invoice_total = float(amount_str)
                currency = self._symbol_to_currency(currency_symbol) if currency_symbol else 'USD'
            except ValueError:
                pass
        
        # Extract vendor
        vendor = self._extract_vendor(text)
        
        # Extract PO number
        po_pattern = r'(?:po|purchase order)[\s#:]*([a-z0-9-]+)'
        po_match = re.search(po_pattern, text, re.IGNORECASE)
        po_number = po_match.group(1) if po_match else None
        
        return {
            "invoice_total": invoice_total,
            "currency": currency,
            "vendor": vendor,
            "po_number": po_number
        }

    def _get_invoice_attachments(self, attachments: List[Dict]) -> List[str]:
        """Get attachments likely to be invoices"""
        invoice_files = []
        for attachment in attachments:
            filename = attachment.get('filename', '').lower()
            mime = attachment.get('mime', '')
            
            if ('invoice' in filename or 'bill' in filename or 
                mime in ['application/pdf', 'image/png', 'image/jpeg']):
                invoice_files.append(attachment.get('filename', ''))
        
        return invoice_files

    def _determine_actions(self, classification: str, email_data: EmailData) -> tuple[List[str], List[str]]:
        """Determine next actions and labels"""
        actions = ["label_email"]
        labels = [f"AI/{classification}"]
        
        if self._has_opt_out(email_data.body):
            labels.append("Opt-Out")
        
        if classification == 'Task':
            actions.extend(["create_task", "draft_reply"])
        elif classification == 'Meeting':
            actions.extend(["create_event", "draft_reply"])
        elif classification == 'Invoice':
            actions.extend(["file_invoice", "draft_reply"])
        elif classification == 'FYI':
            actions.append("draft_reply")
        elif classification == 'Spam':
            if not self._has_opt_out(email_data.body):
                actions = ["label_email"]  # No reply for spam unless opt-out
        
        return actions, labels

    def _generate_summary(self, email_data: EmailData, classification: str) -> str:
        """Generate 1-2 sentence summary"""
        sender = email_data.from_name or email_data.from_email.split('@')[0]
        subject = email_data.subject[:50] + "..." if len(email_data.subject) > 50 else email_data.subject
        
        if classification == 'Task':
            return f"{sender} requests action regarding '{subject}'."
        elif classification == 'Meeting':
            return f"{sender} proposes a meeting about '{subject}'."
        elif classification == 'Invoice':
            return f"{sender} sent an invoice or payment request."
        elif classification == 'Spam':
            return f"Marketing/promotional email from {sender}."
        else:
            return f"{sender} shared information about '{subject}'."

    def _generate_reply(self, email_data: EmailData, classification: str, entities: Dict) -> Dict:
        """Generate reply draft"""
        subject = f"Re: {email_data.subject}"
        
        if classification == 'Task':
            body = self._generate_task_reply(entities)
        elif classification == 'Meeting':
            body = self._generate_meeting_reply(entities)
        elif classification == 'Invoice':
            body = self._generate_invoice_reply(entities)
        elif classification == 'Spam' and self._has_opt_out(email_data.body):
            body = "Please confirm my removal from your mailing list."
        else:
            body = "Thank you for the information. I'll review and follow up if needed."
        
        return {
            "reply": {
                "subject": subject,
                "body": body,
                "send_recommended": False
            }
        }

    def _generate_task_reply(self, entities: Dict) -> str:
        """Generate task-specific reply"""
        if entities.get('due_date'):
            return f"I've noted the task: {entities.get('task_title', 'your request')}. I'll complete this by {entities['due_date']} and update you on progress."
        else:
            return f"I've received your request regarding {entities.get('task_title', 'the task')}. Could you please clarify the expected timeline or deadline?"

    def _generate_meeting_reply(self, entities: Dict) -> str:
        """Generate meeting-specific reply"""
        if entities.get('meeting_start'):
            return f"The proposed time works for me. I'll send a calendar invite with the meeting details. Please confirm the attendee list and any specific agenda items."
        else:
            return "I'd be happy to meet. Could you please suggest a few time slots that work for you? I'm generally available weekdays 9 AM - 5 PM."

    def _generate_invoice_reply(self, entities: Dict) -> str:
        """Generate invoice-specific reply"""
        if entities.get('invoice_total'):
            return f"I've received the invoice for {entities.get('currency', '')} {entities['invoice_total']}. I'll process this and arrange payment according to our terms."
        else:
            return "I've received your invoice. Could you please clarify the total amount due and payment terms?"

    def _generate_reason(self, classification: str, entities: Dict) -> str:
        """Generate reason for classification"""
        if classification == 'Task':
            return "Contains action-oriented language and requests"
        elif classification == 'Meeting':
            return "Contains scheduling or meeting-related content"
        elif classification == 'Invoice':
            return "Contains payment or billing information"
        elif classification == 'Spam':
            return "Contains marketing content or opt-out language"
        else:
            return "Informational content with no clear action required"

    # Helper methods
    def _has_opt_out(self, text: str) -> bool:
        """Check if email contains opt-out language"""
        opt_out_terms = ['unsubscribe', 'opt out', 'remove me', 'stop emails']
        return any(term in text.lower() for term in opt_out_terms)

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        # Simplified date parsing - would need more robust implementation
        try:
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    month, day, year = parts
                    if len(year) == 2:
                        year = '20' + year
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except:
            pass
        return None

    def _format_meeting_time(self, time_tuple: tuple, email_data: EmailData) -> Optional[str]:
        """Format meeting time to ISO format"""
        # Simplified time formatting - would need more robust implementation
        try:
            hour, minute, ampm = time_tuple
            hour = int(hour)
            minute = int(minute)
            
            if ampm and ampm.lower() == 'pm' and hour != 12:
                hour += 12
            elif ampm and ampm.lower() == 'am' and hour == 12:
                hour = 0
            
            # Use today's date as placeholder - would need actual date extraction
            today = datetime.now().strftime('%Y-%m-%d')
            time_str = f"{today}T{hour:02d}:{minute:02d}:00"
            
            if email_data.recipient_timezone:
                # Add timezone offset - simplified
                time_str += "+05:30"  # Default to IST
            
            return time_str
        except:
            return None

    def _extract_vendor(self, text: str) -> Optional[str]:
        """Extract vendor name from text"""
        # Look for "from" patterns
        from_pattern = r'from\s+([A-Za-z\s]+?)(?:\s|$|\.)'
        match = re.search(from_pattern, text, re.IGNORECASE)
        if match:
            vendor = match.group(1).strip()
            if len(vendor) > 3 and len(vendor) < 50:
                return vendor
        return None

    def _symbol_to_currency(self, symbol: str) -> str:
        """Convert currency symbol to ISO code"""
        symbol_map = {'₹': 'INR', '$': 'USD', '€': 'EUR', '£': 'GBP'}
        return symbol_map.get(symbol, 'USD')

def process_email_json(email_json: str) -> str:
    """Process email JSON and return analysis and reply JSON"""
    try:
        email_dict = json.loads(email_json)
        
        # Convert to EmailData object
        email_data = EmailData(
            message_id=email_dict.get('message_id', ''),
            subject=email_dict.get('subject', ''),
            from_name=email_dict.get('from_name', ''),
            from_email=email_dict.get('from_email', ''),
            to_email=email_dict.get('to_email', ''),
            cc_emails=email_dict.get('cc_emails', ''),
            date=email_dict.get('date', ''),
            recipient_timezone=email_dict.get('recipient_timezone'),
            message_link=email_dict.get('message_link'),
            body=email_dict.get('body', ''),
            attachments=email_dict.get('attachments', [])
        )
        
        # Process email
        agent = ActionInbox()
        analysis, reply = agent.process_email(email_data)
        
        # Return both JSON objects
        return json.dumps(analysis, indent=2) + '\n' + json.dumps(reply, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    # Example usage
    sample_email = {
        "message_id": "test@example.com",
        "subject": "Sync on Tue 11:00 IST",
        "from_name": "Rahul",
        "from_email": "rahul@acme.com",
        "to_email": "user@company.com",
        "cc_emails": "",
        "date": "Mon, 25 Aug 2025 10:00:00 +0530",
        "recipient_timezone": "Asia/Kolkata",
        "message_link": None,
        "body": "Hi, can we have a 30-min sync on Tuesday at 11:00 IST to discuss Q3 deliverables? I'll send a Google Meet link.",
        "attachments": []
    }
    
    result = process_email_json(json.dumps(sample_email))
    print(result)