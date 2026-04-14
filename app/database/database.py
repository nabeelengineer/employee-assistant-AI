
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./employee_assistant.db")

# Create SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite specific configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        poolclass=StaticPool,
        echo=True
    )
else:
    # PostgreSQL/MySQL configuration
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=True
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_database():
    try:
        # Import all models to ensure they are registered
        from ..models.task import TaskDB
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def close_database():
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

def check_database_connection():
    try:
        # Try to execute a simple query
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        
        logger.info("Database connection check: SUCCESS")
        return True
        
    except Exception as e:
        logger.error(f"Database connection check: FAILED - {e}")
        return False

def get_database_info():
    try:
        # Get database URL (without password)
        db_url = DATABASE_URL
        if "@" in db_url and ":" in db_url.split("@")[0]:
            parts = db_url.split("@")
            user_pass = parts[0].split(":")
            if len(user_pass) > 2:
                safe_url = f"{user_pass[0]}:***@{parts[1]}"
            else:
                safe_url = db_url
        else:
            safe_url = db_url
        
        # Check if database file exists for SQLite
        db_file_exists = False
        if db_url.startswith("sqlite"):
            db_file = db_url.replace("sqlite:///", "")
            db_file_exists = os.path.exists(db_file)
        
        return {
            "database_url": safe_url,
            "database_type": "SQLite" if db_url.startswith("sqlite") else "Other",
            "connection_status": "Connected" if check_database_connection() else "Disconnected",
            "database_file_exists": db_file_exists if db_url.startswith("sqlite") else None
        }
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {
            "error": str(e)
        }

# Database health check
class DatabaseHealthCheck:
    
    @staticmethod
    def is_healthy():
        return check_database_connection()
    
    @staticmethod
    def get_status():
        info = get_database_info()
        return {
            "status": "healthy" if check_database_connection() else "unhealthy",
            "details": info
        }
