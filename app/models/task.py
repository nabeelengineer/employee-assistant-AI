
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Import Base from database module
from ..database.database import Base

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

# SQLAlchemy Database Model
class TaskDB(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assignee = Column(String(100), nullable=True)
    priority = Column(String(20), default=TaskPriority.MEDIUM)
    status = Column(String(20), default=TaskStatus.PENDING)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(100), nullable=True)
    
    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"

# Pydantic Models for API
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    assignee: Optional[str] = Field(None, max_length=100, description="Person assigned to task")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Due date for task")

class TaskCreate(TaskBase):
    created_by: Optional[str] = Field(None, description="Who created the task")

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    assignee: Optional[str] = Field(None, max_length=100)
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None

class TaskResponse(TaskBase):
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class TaskList(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    per_page: int

# Task Manager Class
class TaskManager:
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_task(self, task_data: TaskCreate) -> TaskResponse:
        db_task = TaskDB(
            title=task_data.title,
            description=task_data.description,
            assignee=task_data.assignee,
            priority=task_data.priority.value,
            due_date=task_data.due_date,
            created_by=task_data.created_by
        )
        
        # Add to database
        self.db.add(db_task)
        self.db.commit()
        self.db.refresh(db_task)
        
        return TaskResponse.from_orm(db_task)
    
    def get_task(self, task_id: int) -> Optional[TaskResponse]:
        task = self.db.query(TaskDB).filter(TaskDB.id == task_id).first()
        if task:
            return TaskResponse.from_orm(task)
        return None
    
    def get_all_tasks(self, skip: int = 0, limit: int = 100, 
                     status: Optional[TaskStatus] = None,
                     assignee: Optional[str] = None) -> TaskList:
        query = self.db.query(TaskDB)
        
        # Apply filters
        if status:
            query = query.filter(TaskDB.status == status.value)
        if assignee:
            query = query.filter(TaskDB.assignee == assignee)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        tasks = query.order_by(TaskDB.created_at.desc()).offset(skip).limit(limit).all()
        
        return TaskList(
            tasks=[TaskResponse.from_orm(task) for task in tasks],
            total=total,
            page=skip // limit + 1,
            per_page=limit
        )
    
    def update_task(self, task_id: int, task_data: TaskUpdate) -> Optional[TaskResponse]:
        task = self.db.query(TaskDB).filter(TaskDB.id == task_id).first()
        if not task:
            return None
        
        # Update fields
        if task_data.title is not None:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.assignee is not None:
            task.assignee = task_data.assignee
        if task_data.priority is not None:
            task.priority = task_data.priority.value
        if task_data.status is not None:
            task.status = task_data.status.value
            if task_data.status == TaskStatus.COMPLETED and not task.completed_at:
                task.completed_at = datetime.now()
        if task_data.due_date is not None:
            task.due_date = task_data.due_date
        
        # Update timestamp
        task.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(task)
        
        return TaskResponse.from_orm(task)
    
    def delete_task(self, task_id: int) -> bool:
        task = self.db.query(TaskDB).filter(TaskDB.id == task_id).first()
        if not task:
            return False
        
        self.db.delete(task)
        self.db.commit()
        return True
    
    def get_overdue_tasks(self) -> List[TaskResponse]:
        now = datetime.now()
        tasks = self.db.query(TaskDB).filter(
            TaskDB.due_date < now,
            TaskDB.status != TaskStatus.COMPLETED
        ).all()
        
        return [TaskResponse.from_orm(task) for task in tasks]
    
    def get_tasks_by_assignee(self, assignee: str) -> List[TaskResponse]:
        tasks = self.db.query(TaskDB).filter(TaskDB.assignee == assignee).all()
        return [TaskResponse.from_orm(task) for task in tasks]
    
    def get_task_statistics(self) -> dict:
        total_tasks = self.db.query(TaskDB).count()
        completed_tasks = self.db.query(TaskDB).filter(TaskDB.status == TaskStatus.COMPLETED).count()
        pending_tasks = self.db.query(TaskDB).filter(TaskDB.status == TaskStatus.PENDING).count()
        in_progress_tasks = self.db.query(TaskDB).filter(TaskDB.status == TaskStatus.IN_PROGRESS).count()
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
