
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import ssl
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
import os
from dataclasses import dataclass
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmailMessage:
    id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    body: str
    attachments: List[str] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []

@dataclass
class EmailAnalysis:
    summary: str
    action_items: List[str]
    priority: str
    category: str
    should_reply: bool
    suggested_reply: Optional[str] = None

class EmailService:
    
    def __init__(self, email_config: Dict[str, str]):
        self.host = email_config.get('EMAIL_HOST', 'imap.gmail.com')
        self.port = email_config.get('EMAIL_PORT', 993)
        self.username = email_config.get('EMAIL_USERNAME')
        self.password = email_config.get('EMAIL_PASSWORD')
        self.smtp_host = email_config.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = email_config.get('SMTP_PORT', 587)
        
        # Initialize AI processor for email analysis
        from ..core.ai_processor import AIProcessor
        self.ai_processor = AIProcessor()
    
    def connect_imap(self) -> Optional[imaplib.IMAP4_SSL]:
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            
            # Login
            mail.login(self.username, self.password)
            
            logger.info(f"Successfully connected to IMAP server: {self.host}")
            return mail
            
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return None
    
    def fetch_emails(self, folder: str = 'INBOX', limit: int = 50, 
                     since_days: int = 7) -> List[EmailMessage]:
        mail = None
        try:
            # Connect to server
            mail = self.connect_imap()
            if not mail:
                return []
            
            # Select folder
            mail.select(folder)
            
            # Calculate date filter
            date_filter = (datetime.now() - timedelta(days=since_days)).strftime('%d-%b-%Y')
            
            # Search for emails
            search_criteria = f'(SINCE {date_filter})'
            status, messages = mail.search(None, search_criteria)
            
            if status != 'OK':
                logger.error("Failed to search for emails")
                return []
            
            # Get email IDs
            email_ids = messages[0].split()
            
            # Limit the number of emails
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            
            emails = []
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extract email information
                    email_msg = self._parse_email(msg, email_id.decode())
                    if email_msg:
                        emails.append(email_msg)
                        
                except Exception as e:
                    logger.error(f"Error parsing email {email_id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(emails)} emails from {folder}")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
        
        finally:
            if mail:
                mail.close()
                mail.logout()
    
    def _parse_email(self, msg, email_id: str) -> Optional[EmailMessage]:
        try:
            # Extract basic headers
            subject = msg['subject'] or 'No Subject'
            sender = msg['from'] or 'Unknown Sender'
            recipient = msg['to'] or 'Unknown Recipient'
            
            # Parse date
            date_str = msg['date']
            if date_str:
                try:
                    date = email.utils.parsedate_to_datetime(date_str)
                except:
                    date = datetime.now()
            else:
                date = datetime.now()
            
            # Extract body
            body = self._extract_email_body(msg)
            
            return EmailMessage(
                id=email_id,
                subject=subject,
                sender=sender,
                recipient=recipient,
                date=date,
                body=body
            )
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    def _extract_email_body(self, msg) -> str:
        body = ""
        
        if msg.is_multipart():
            # Handle multipart messages
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" not in content_disposition:
                    try:
                        # Get text content
                        if content_type == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                        elif content_type == "text/html":
                            # For HTML emails, you might want to strip HTML tags. For now, we'll use as-is
                            body = part.get_payload(decode=True).decode()
                            break
                    except:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                body = str(msg.get_payload())
        
        return body
    
    def analyze_email(self, email_msg: EmailMessage) -> EmailAnalysis:
        analysis_result = self.ai_processor.analyze_email_content(email_msg.body)
        
        should_reply = self._should_reply(email_msg)
        
        suggested_reply = None
        if should_reply:
            suggested_reply = self._generate_reply_suggestion(email_msg, analysis_result)
        
        category = self._categorize_email(email_msg)
        
        return EmailAnalysis(
            summary=analysis_result['summary'],
            action_items=analysis_result['action_items'],
            priority=analysis_result['priority'],
            category=category,
            should_reply=should_reply,
            suggested_reply=suggested_reply
        )
    
    def _should_reply(self, email_msg: EmailMessage) -> bool:
        if self.username in email_msg.sender:
            return False
        
        # Don't reply to automated emails
        automated_patterns = [
            r'no-reply@', r'noreply@', r'do-not-reply@',
            r'notification@', r'alert@', r'system@'
        ]
        
        for pattern in automated_patterns:
            if re.search(pattern, email_msg.sender, re.IGNORECASE):
                return False
        
        # Reply to direct questions
        question_indicators = ['?', 'help', 'assist', 'support', 'please']
        body_lower = email_msg.body.lower()
        
        return any(indicator in body_lower for indicator in question_indicators)
    
    def _generate_reply_suggestion(self, email_msg: EmailMessage, 
                                 analysis: Dict) -> str:
        recipient_name = email_msg.sender.split('@')[0].title()
        
        if analysis['action_items']:
            reply = f"Hi {recipient_name},\n\n"
            reply += "Thank you for your email. I've received your message and "
            reply += "noted the following action items:\n\n"
            
            for i, item in enumerate(analysis['action_items'], 1):
                reply += f"{i}. {item.title()}\n"
            
            reply += "\nI'll work on these items and keep you updated.\n\n"
            reply += "Best regards,\nEmployee Assistant AI"
            
        else:
            reply = f"Hi {recipient_name},\n\n"
            reply += "Thank you for your email. I've received your message and "
            reply += "will review it shortly. If there's anything specific you "
            reply += "need help with, please let me know.\n\n"
            reply += "Best regards,\nEmployee Assistant AI"
        
        return reply
    
    def _categorize_email(self, email_msg: EmailMessage) -> str:
        subject_lower = email_msg.subject.lower()
        body_lower = email_msg.body.lower()
        
        # Define categories and their keywords
        categories = {
            'urgent': ['urgent', 'asap', 'immediate', 'emergency'],
            'task': ['task', 'assign', 'complete', 'deadline', 'project'],
            'meeting': ['meeting', 'schedule', 'appointment', 'call'],
            'information': ['fyi', 'information', 'update', 'notice'],
            'question': ['question', 'help', 'how to', 'what is'],
            'report': ['report', 'analysis', 'data', 'statistics']
        }
        
        # Check for category keywords
        for category, keywords in categories.items():
            if any(keyword in subject_lower or keyword in body_lower 
                   for keyword in keywords):
                return category
        
        return 'general'
    
    def send_email(self, to_email: str, subject: str, body: str, 
                  cc_email: str = None) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc_email:
                msg['Cc'] = cc_email
            
            msg.attach(MIMEText(body, 'plain'))
            
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls(context=context)
            server.login(self.username, self.password)
            
            # Send email
            recipients = [to_email]
            if cc_email:
                recipients.append(cc_email)
            
            server.send_message(msg, to_addrs=recipients)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def create_tasks_from_emails(self, emails: List[EmailMessage]) -> List[Dict]:
        tasks = []
        
        for email_msg in emails:
            analysis = self.analyze_email(email_msg)
            
            for action_item in analysis.action_items:
                task_data = {
                    'title': f"Email Task: {action_item[:50]}...",
                    'description': f"Task from email: {email_msg.subject}\n\n"
                                 f"From: {email_msg.sender}\n"
                                 f"Action: {action_item}",
                    'priority': analysis.priority,
                    'source': 'email',
                    'source_id': email_msg.id
                }
                tasks.append(task_data)
        
        return tasks
    
    def get_email_summary(self, emails: List[EmailMessage]) -> Dict:
        if not emails:
            return {'total': 0, 'categories': {}, 'senders': {}}
        
        categories = {}
        senders = {}
        urgent_count = 0
        
        for email_msg in emails:
            analysis = self.analyze_email(email_msg)
            
            category = analysis.category
            categories[category] = categories.get(category, 0) + 1
            
            sender = email_msg.sender
            senders[sender] = senders.get(sender, 0) + 1
            
            if analysis.priority == 'high':
                urgent_count += 1
        
        return {
            'total': len(emails),
            'categories': categories,
            'senders': senders,
            'urgent_count': urgent_count,
            'date_range': {
                'start': min(email.date for email in emails).isoformat(),
                'end': max(email.date for email in emails).isoformat()
            }
        }
