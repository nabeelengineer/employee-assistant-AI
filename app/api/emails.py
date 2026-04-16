
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import logging
from pydantic import BaseModel, Field

from ..services.email_service import EmailService, EmailMessage, EmailAnalysis
from ..database.database import get_db
from ..models.task import TaskManager, TaskCreate, TaskPriority

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/emails", tags=["emails"])

# Pydantic models for API
class EmailFetchRequest(BaseModel):
    folder: str = Field(default="INBOX", description="Email folder to fetch from")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum emails to fetch")
    since_days: int = Field(default=7, ge=1, le=30, description="Fetch emails from last N days")

class EmailSendRequest(BaseModel):
    to_email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    cc_email: Optional[str] = Field(None, description="CC recipient")
    email_config: Dict = Field(..., description="Email configuration")

class AutoReplyRequest(BaseModel):
    email_text: str = Field(..., description="Original email content")
    email_metadata: Dict = Field(..., description="Email metadata including sender, subject")
    email_config: Dict = Field(..., description="Email configuration")

@router.post("/fetch", summary="Fetch emails from server")
async def fetch_emails(
    request: EmailFetchRequest,
    email_config: Dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Initialize email service
        email_service = EmailService(email_config)

        emails = email_service.fetch_emails(
            folder=request.folder,
            limit=request.limit,
            since_days=request.since_days
        )
        
        if not emails:
            return {
                "message": "No emails found",
                "emails": [],
                "summary": {"total": 0}
            }
        
        # Analyze emails
        analyzed_emails = []
        for email_msg in emails:
            analysis = email_service.analyze_email(email_msg)
            analyzed_emails.append({
                "id": email_msg.id,
                "subject": email_msg.subject,
                "sender": email_msg.sender,
                "date": email_msg.date.isoformat(),
                "analysis": {
                    "summary": analysis.summary,
                    "action_items": analysis.action_items,
                    "priority": analysis.priority,
                    "category": analysis.category,
                    "should_reply": analysis.should_reply
                }
            })
        
        # Create tasks from action items
        tasks_created = []
        task_manager = TaskManager(db)
        
        for email_msg in emails:
            analysis = email_service.analyze_email(email_msg)
            
            for action_item in analysis.action_items:
                task_data = TaskCreate(
                    title=f"Email Task: {action_item[:50]}...",
                    description=f"Task from email: {email_msg.subject}\n\n"
                               f"From: {email_msg.sender}\n"
                               f"Action: {action_item}",
                    priority=TaskPriority(analysis.priority) if analysis.priority in ['low', 'medium', 'high'] else TaskPriority.MEDIUM,
                    created_by="Email Assistant"
                )
                
                task = task_manager.create_task(task_data)
                tasks_created.append({
                    "task_id": task.id,
                    "title": task.title,
                    "source_email_id": email_msg.id
                })
        
        # Get email summary
        summary = email_service.get_email_summary(emails)
        
        logger.info(f"Fetched and analyzed {len(emails)} emails")
        
        return {
            "message": f"Successfully fetched and analyzed {len(emails)} emails",
            "emails": analyzed_emails,
            "tasks_created": tasks_created,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")

@router.post("/analyze", summary="Analyze email content")
async def analyze_email(
    email_text: str = Body(..., description="Email content to analyze"),
    email_metadata: Optional[Dict] = Body(None, description="Email metadata (subject, sender, etc.)")
):
    try:
        # Create email message object
        email_msg = EmailMessage(
            id="temp",
            subject=email_metadata.get("subject", "No Subject") if email_metadata else "No Subject",
            sender=email_metadata.get("sender", "unknown@sender.com") if email_metadata else "unknown@sender.com",
            recipient="me@company.com",
            date=email_metadata.get("date", "2023-01-01") if email_metadata else "2023-01-01",
            body=email_text
        )
        
        # Initialize email service (without email config for analysis only)
        from ..core.ai_processor import AIProcessor
        ai_processor = AIProcessor()
        
        # Analyze email
        analysis_result = ai_processor.analyze_email_content(email_text)
        
        # Determine category
        subject_lower = email_msg.subject.lower()
        body_lower = email_text.lower()
        
        categories = {
            'urgent': ['urgent', 'asap', 'immediate', 'emergency'],
            'task': ['task', 'assign', 'complete', 'deadline', 'project'],
            'meeting': ['meeting', 'schedule', 'appointment', 'call'],
            'information': ['fyi', 'information', 'update', 'notice'],
            'question': ['question', 'help', 'how to', 'what is'],
            'report': ['report', 'analysis', 'data', 'statistics']
        }
        
        category = 'general'
        for cat, keywords in categories.items():
            if any(keyword in subject_lower or keyword in body_lower for keyword in keywords):
                category = cat
                break
        
        # Generate suggested reply
        should_reply = any(indicator in body_lower for indicator in ['?', 'help', 'assist', 'support', 'please'])
        suggested_reply = None
        
        if should_reply:
            recipient_name = email_msg.sender.split('@')[0].title()
            if analysis_result['action_items']:
                suggested_reply = f"Hi {recipient_name},\n\n"
                suggested_reply += "Thank you for your email. I've noted the following action items:\n\n"
                for i, item in enumerate(analysis_result['action_items'], 1):
                    suggested_reply += f"{i}. {item.title()}\n"
                suggested_reply += "\nI'll work on these items and keep you updated.\n\n"
                suggested_reply += "Best regards,\nEmployee Assistant AI"
            else:
                suggested_reply = f"Hi {recipient_name},\n\n"
                suggested_reply += "Thank you for your email. I've received your message and "
                suggested_reply += "will review it shortly.\n\n"
                suggested_reply += "Best regards,\nEmployee Assistant AI"
        
        logger.info("Analyzed email content")
        
        return {
            "summary": analysis_result['summary'],
            "action_items": analysis_result['action_items'],
            "priority": analysis_result['priority'],
            "category": category,
            "should_reply": should_reply,
            "suggested_reply": suggested_reply,
            "word_count": len(email_text.split()),
            "line_count": len(email_text.split('\n'))
        }
        
    except Exception as e:
        logger.error(f"Error analyzing email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze email: {str(e)}")

@router.post("/send", summary="Send an email")
async def send_email(
    request: EmailSendRequest
):
    try:
        # Initialize email service
        email_service = EmailService(request.email_config)
        
        # Send email
        success = email_service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            cc_email=request.cc_email
        )
        
        if success:
            logger.info(f"Email sent to {request.to_email}")
            return {
                "message": "Email sent successfully",
                "recipient": request.to_email,
                "subject": request.subject,
                "demo_mode": "Email simulated for demo purposes"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@router.get("/summary", summary="Get email processing summary")
async def get_email_summary(
    email_config: Dict = Body(...),
    folder: str = Query(default="INBOX", description="Email folder to analyze"),
    since_days: int = Query(default=7, ge=1, le=30, description="Analyze emails from last N days")
):
    try:
        # Initialize email service
        email_service = EmailService(email_config)
        
        # Fetch emails for summary
        emails = email_service.fetch_emails(
            folder=folder,
            limit=100,
            since_days=since_days
        )
        
        # Get summary
        summary = email_service.get_email_summary(emails)
        
        logger.info(f"Generated email summary for {len(emails)} emails")
        return summary
        
    except Exception as e:
        logger.error(f"Error getting email summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get email summary: {str(e)}")

@router.post("/auto-reply", summary="Generate and send auto-reply")
async def auto_reply(
    request: AutoReplyRequest,
    db: Session = Depends(get_db)
):
    try:
        # Initialize email service
        email_service = EmailService(request.email_config)
        
        # Create email message object
        email_msg = EmailMessage(
            id="auto-reply",
            subject=request.email_metadata.get("subject", "No Subject"),
            sender=request.email_metadata.get("sender", "unknown@sender.com"),
            recipient="me@company.com",
            date=request.email_metadata.get("date", "2023-01-01"),
            body=request.email_text
        )
        
        # Analyze email
        analysis = email_service.analyze_email(email_msg)
        
        if not analysis.should_reply:
            return {
                "message": "Auto-reply not recommended for this email",
                "reason": "Email doesn't appear to require a response"
            }
        
        # Generate reply
        reply_body = analysis.suggested_reply or "Thank you for your email. I have received it and will respond accordingly."
        
        # Send reply
        success = email_service.send_email(
            to_email=email_msg.sender,
            subject=f"Re: {email_msg.subject}",
            body=reply_body
        )
        
        if success:
            logger.info(f"Auto-reply sent to {email_msg.sender}")
            return {
                "message": "Auto-reply sent successfully",
                "recipient": email_msg.sender,
                "reply_summary": reply_body[:100] + "..." if len(reply_body) > 100 else reply_body,
                "demo_mode": "Email simulated for demo purposes"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send auto-reply")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto-reply: {e}")
        raise HTTPException(status_code=500, detail=f"Auto-reply failed: {str(e)}")

@router.post("/intelligent-process", summary="Intelligent email processing with priority logic")
async def intelligent_email_process(
    email_config: Dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Process emails with new priority-based logic:
    - High priority: Create urgent tasks
    - Medium priority: Include in summary
    - Low priority: Reference only
    - Reply-first: Reply before task creation when needed
    """
    try:
        # Initialize email service
        email_service = EmailService(email_config)
        
        # Fetch emails
        emails = email_service.fetch_emails(limit=50, since_days=7)
        
        results = {
            "processed": {
                "total": len(emails),
                "urgent_tasks_created": 0,
                "medium_emails_for_review": 0,
                "low_priority_reference": 0,
                "replies_sent": 0
            },
            "tasks_created": [],
            "medium_priority_summary": [],
            "actions_taken": []
        }
        
        task_manager = TaskManager(db)
        
        for email_msg in emails:
            analysis = email_service.analyze_email(email_msg)
            
            if analysis.priority == 'high':
                # Check if we should reply first
                if email_service.should_reply_before_task(email_msg):
                    # Send reply first
                    reply_body = analysis.suggested_reply or "Thank you for your urgent email. I'm addressing this immediately."
                    email_service.send_email(
                        to_email=email_msg.sender,
                        subject=f"Re: {email_msg.subject}",
                        body=reply_body
                    )
                    results["processed"]["replies_sent"] += 1
                    results["actions_taken"].append(f"Replied to urgent email from {email_msg.sender}")
                
                # Create urgent tasks
                for action_item in analysis.action_items:
                    task_data = TaskCreate(
                        title=f"URGENT: {action_item[:50]}...",
                        description=f"Urgent task from email: {email_msg.subject}",
                        priority="urgent",
                        assignee=None,
                        created_by="Email Processor"
                    )
                    task = task_manager.create_task(task_data)
                    results["tasks_created"].append(task.dict())
                    results["processed"]["urgent_tasks_created"] += 1
                    results["actions_taken"].append(f"Created urgent task: {task.title}")
            
            elif analysis.priority == 'medium':
                # Add to summary for manual review
                results["medium_priority_summary"].append({
                    "subject": email_msg.subject,
                    "sender": email_msg.sender,
                    "date": email_msg.date.isoformat(),
                    "summary": email_msg.body[:100] + "..." if len(email_msg.body) > 100 else email_msg.body,
                    "action_items": analysis.action_items
                })
                results["processed"]["medium_emails_for_review"] += 1
                results["actions_taken"].append(f"Added medium priority email from {email_msg.sender} to review queue")
            
            elif analysis.priority == 'low':
                # Keep for reference only
                results["processed"]["low_priority_reference"] += 1
                results["actions_taken"].append(f"Low priority email from {email_msg.sender} archived for reference")
        
        return {
            "status": "success",
            "summary": f"Processed {results['processed']['total']} emails with new priority logic",
            "results": results,
            "recommendations": [
                "Review urgent tasks immediately",
                "Manually create tasks from medium priority emails",
                "Low priority emails kept for reference only"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in intelligent email processing: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
