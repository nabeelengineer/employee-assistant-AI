
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import openai
from dataclasses import dataclass

@dataclass
class Intent:
    action: str  # create_task, query, email_process, etc.
    confidence: float  # How confident we are about this intent
    entities: Dict[str, str]  # Extracted information

@dataclass
class TaskInfo:
    title: str
    description: str
    assignee: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None

class AIProcessor:
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key
        if openai_api_key:
            openai.api_key = openai_api_key
        
        # Define intent patterns
        self.intent_patterns = {
            'create_task': [
                r'create.*task', r'add.*task', r'new.*task', r'make.*task',
                r'assign.*task', r'set.*task', r'need.*task'
            ],
            'query': [
                r'what.*is', r'how.*to', r'tell.*me', r'show.*me',
                r'find.*', r'search.*', r'look.*for', r'information'
            ],
            'email_process': [
                r'email.*process', r'reply.*email', r'summarize.*email',
                r'check.*email', r'email.*summary'
            ],
            'notification': [
                r'send.*notification', r'notify.*', r'alert.*',
                r'remind.*', r'inform.*'
            ]
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'date': [
                r'\b(today|tomorrow|yesterday)\b',
                r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b \d{1,2}\b',
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',
                r'\b\d{1,2}-\d{1,2}-\d{4}\b'
            ],
            'priority': [
                r'\b(high|urgent|critical|important)\b',
                r'\b(medium|normal|regular)\b',
                r'\b(low|minor|casual)\b'
            ],
            'person': [
                r'\b(john|jane|bob|alice|mike|sarah|david|lisa)\b',
                r'\b\w+\s+\w+\b'
            ]
        }
    
    def detect_intent(self, text: str) -> Intent:
        text_lower = text.lower()
        best_match = None
        best_confidence = 0.0
        
        # Check each intent pattern
        for action, patterns in self.intent_patterns.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    matches += 1
            
            confidence = matches / len(patterns)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = action
        
        # Extract entities
        entities = self.extract_entities(text)
        
        return Intent(
            action=best_match or 'unknown',
            confidence=best_confidence,
            entities=entities
        )
    
    def extract_entities(self, text: str) -> Dict[str, str]:
        entities = {}
        
        # Extract dates
        dates = []
        for pattern in self.entity_patterns['date']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        if dates:
            entities['dates'] = dates
        
        # Extract priority
        for pattern in self.entity_patterns['priority']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities['priority'] = match.group(1)
                break
        
        # Extract people
        people = []
        for pattern in self.entity_patterns['person']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            people.extend(matches)
        
        if people:
            entities['people'] = people
        
        return entities
    
    def parse_task_from_text(self, text: str) -> Optional[TaskInfo]:
        intent = self.detect_intent(text)
        
        if intent.action != 'create_task':
            return None
        
        # Extract task title (first sentence or main action)
        title = text.split('.')[0].strip()
        if len(title) > 50:
            title = title[:47] + "..."
        
        # Extract description (full text)
        description = text.strip()
        
        # Get assignee from entities
        assignee = None
        if 'people' in intent.entities and intent.entities['people']:
            assignee = intent.entities['people'][0]
        
        # Get priority from entities
        priority = intent.entities.get('priority', 'medium')
        
        # Get due date from entities
        due_date = None
        if 'dates' in intent.entities and intent.entities['dates']:
            due_date = self.convert_date_to_format(intent.entities['dates'][0])
        
        return TaskInfo(
            title=title,
            description=description,
            assignee=assignee,
            priority=priority,
            due_date=due_date
        )
    
    def convert_date_to_format(self, date_str: str) -> str:
        date_str = date_str.lower().strip()
        
        # Handle relative dates
        if date_str == 'today':
            return datetime.now().strftime('%Y-%m-%d')
        elif date_str == 'tomorrow':
            return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        elif date_str == 'yesterday':
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Handle day names
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if date_str in days_of_week:
            today = datetime.now()
            current_day = today.weekday()  # 0 = Monday, 6 = Sunday
            target_day = days_of_week.index(date_str)
            
            days_ahead = target_day - current_day
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            
            target_date = today + timedelta(days=days_ahead)
            return target_date.strftime('%Y-%m-%d')
        
        # For other formats, return as-is for now In a real implementation, you'd use dateutil.parser
        return date_str
    
    def generate_response(self, intent: Intent, context: Dict = None) -> str:
        context = context or {}
        
        if intent.action == 'create_task':
            return "I'll help you create that task! I've extracted the details and added it to your task list."
        
        elif intent.action == 'query':
            return "I'm searching for that information. Let me find what you're looking for..."
        
        elif intent.action == 'email_process':
            return "I'll process those emails for you. I can summarize them and extract any action items."
        
        elif intent.action == 'notification':
            return "I'll send that notification out to the relevant team members."
        
        else:
            return "I'm here to help! You can ask me to create tasks, handle emails, or find information."
    
    def analyze_email_content(self, email_text: str) -> Dict:
        analysis = {
            'summary': '',
            'action_items': [],
            'priority': 'medium',
            'sender_intent': 'information'
        }
        
        # Simple rule-based analysis
        text_lower = email_text.lower()
        
        # Detect urgency
        urgent_words = ['urgent', 'asap', 'immediately', 'critical', 'emergency']
        if any(word in text_lower for word in urgent_words):
            analysis['priority'] = 'high'
        
        # Extract action items
        action_patterns = [
            r'please\s+(.+)',
            r'can\s+you\s+(.+)',
            r'need\s+to\s+(.+)',
            r'action\s+item:\s*(.+)'
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            analysis['action_items'].extend(matches)
        
        # Generate simple summary
        analysis['summary'] = email_text[:100] + "..." if len(email_text) > 100 else email_text
        
        return analysis
