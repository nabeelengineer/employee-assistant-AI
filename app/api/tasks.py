
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ..models.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskList, 
    TaskStatus, TaskPriority, TaskManager
)
from ..core.ai_processor import AIProcessor
from ..database.database import get_db

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse, summary="Create a new task")
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    try:
        task_manager = TaskManager(db)
        task = task_manager.create_task(task_data)
        
        logger.info(f"Created task: {task.id} - {task.title}")
        return task
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/from-text", response_model=TaskResponse, summary="Create task from natural language")
async def create_task_from_text(
    request: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Extract text from request
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Text field is required")
        
        # Use AI processor to parse the text
        ai_processor = AIProcessor()
        task_info = ai_processor.parse_task_from_text(text)
        
        if not task_info:
            raise HTTPException(
                status_code=400, 
                detail="Could not parse task creation request from the provided text"
            )
        
        # Create task data
        task_data = TaskCreate(
            title=task_info.title,
            description=task_info.description,
            assignee=task_info.assignee,
            priority=TaskPriority(task_info.priority),
            due_date=None
        )
        
        # Create the task
        task_manager = TaskManager(db)
        task = task_manager.create_task(task_data)
        
        logger.info(f"Created task from AI: {task.id} - {task.title}")
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task from text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=TaskList, summary="Get all tasks")
async def get_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of tasks to return"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    assignee: Optional[str] = Query(None, description="Filter by assignee name"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    db: Session = Depends(get_db)
):
    try:
        task_manager = TaskManager(db)
        tasks = task_manager.get_all_tasks(
            skip=skip, 
            limit=limit, 
            status=status,
            assignee=assignee
        )
        
        logger.info(f"Retrieved {len(tasks.tasks)} tasks")
        return tasks
        
    except Exception as e:
        logger.error(f"Error retrieving tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}", response_model=TaskResponse, summary="Get a specific task")
async def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    try:
        task_manager = TaskManager(db)
        task = task_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{task_id}", response_model=TaskResponse, summary="Update a task")
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db)
):
    try:
        task_manager = TaskManager(db)
        task = task_manager.update_task(task_id, task_data)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"Updated task {task_id}")
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}", summary="Delete a task")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    try:
        task_manager = TaskManager(db)
        success = task_manager.delete_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"Deleted task {task_id}")
        return {"message": "Task deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overdue/", response_model=List[TaskResponse], summary="Get overdue tasks")
async def get_overdue_tasks(db: Session = Depends(get_db)):
    try:
        task_manager = TaskManager(db)
        overdue_tasks = task_manager.get_overdue_tasks()
        
        logger.info(f"Found {len(overdue_tasks)} overdue tasks")
        return overdue_tasks
        
    except Exception as e:
        logger.error(f"Error retrieving overdue tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assignee/{assignee}", response_model=List[TaskResponse], summary="Get tasks by assignee")
async def get_tasks_by_assignee(
    assignee: str,
    db: Session = Depends(get_db)
):
    try:
        task_manager = TaskManager(db)
        tasks = task_manager.get_tasks_by_assignee(assignee)
        
        logger.info(f"Retrieved {len(tasks)} tasks for {assignee}")
        return tasks
        
    except Exception as e:
        logger.error(f"Error retrieving tasks for {assignee}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics/", summary="Get task statistics")
async def get_task_statistics(db: Session = Depends(get_db)):
    try:
        task_manager = TaskManager(db)
        stats = task_manager.get_task_statistics()
        
        logger.info("Retrieved task statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving task statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{task_id}/complete", response_model=TaskResponse, summary="Mark task as completed")
async def complete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    try:
        task_manager = TaskManager(db)
        task = task_manager.update_task(task_id, TaskUpdate(status=TaskStatus.COMPLETED))
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"Completed task {task_id}")
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
