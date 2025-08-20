"""
FastAPI dependency injection functions.

This module provides dependency functions that can be injected into
FastAPI route handlers for database sessions, Redis connections, etc.
"""

from typing import Generator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import get_redis, RedisManager


# Re-export database dependency
def get_database() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    yield from get_db()


# Re-export Redis dependency  
def get_redis_manager() -> RedisManager:
    """
    FastAPI dependency for Redis manager.
    
    Returns:
        RedisManager: Redis connection manager
    """
    return get_redis()
