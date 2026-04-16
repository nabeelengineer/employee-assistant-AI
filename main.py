
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import uvicorn
import os

# Load environment variables
load_dotenv()

# Create FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Employee Assistant AI...")
    print("=" * 50)
    
    # Initialize database
    try:
        init_database()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
    
    # Check database connection
    if check_database_connection():
        print("Database connection: OK")
    else:
        print("Database connection: FAILED")
    
    print("Features available:")
    print("1. Natural Language Query Processing")
    print("2. Task Management System")
    print("3. Email Automation")
    print("4. System Log Analysis")
    print("5. Notification System")
    print("=" * 50)
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 50)
    
    yield
    
    # Shutdown
    print("Shutting down Employee Assistant AI...")
    close_database()

app = FastAPI(
    title="Employee Assistant AI",
    description="An AI-powered system for employee task management, email processing, and automation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers and database
from app.api import api_router
from app.database.database import init_database, check_database_connection, close_database

# Include API router
app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Employee Assistant AI!",
        "features": [
            "Employee query handling",
            "Task management",
            "Email processing", 
            "Log analysis",
            "Automated notifications"
        ],
        "status": "Active"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Employee Assistant AI"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
