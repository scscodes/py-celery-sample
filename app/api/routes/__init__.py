"""
API routes package.

This package contains all FastAPI route modules organized by domain.
Each module provides REST endpoints for specific business functionality.
"""

# Import all route modules for easy access
from app.api.routes import users, groups, computers, incidents, tasks, monitoring

__all__ = [
    "users",
    "groups", 
    "computers",
    "incidents",
    "tasks",
    "monitoring"
]
