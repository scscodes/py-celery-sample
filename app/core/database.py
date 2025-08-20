"""
Database configuration and setup for SQLAlchemy.

This module handles database connection management, session creation,
and provides the foundation for all database operations in the application.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config.settings import settings


# Create SQLAlchemy engine
# For SQLite, we need check_same_thread=False to allow multiple threads
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug  # Log SQL queries when in debug mode
)

# Create SessionLocal class for database sessions
# Each instance will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy models
# All models will inherit from this base class
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency function to get database session.
    
    This function creates a new database session for each request
    and ensures it's properly closed after the request completes.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables.
    
    This function creates all tables defined by SQLAlchemy models
    that inherit from Base. Used for initial database setup.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables.
    
    This function drops all tables defined by SQLAlchemy models.
    Useful for testing or resetting the database.
    """
    Base.metadata.drop_all(bind=engine)
