
from fastapi import APIRouter
from . import tasks, emails

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(tasks.router)
api_router.include_router(emails.router)
