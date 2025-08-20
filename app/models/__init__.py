"""
Database models package.

This module imports all SQLAlchemy models to ensure they are
registered with the database metadata for table creation.
"""

# Import all models to register them with SQLAlchemy
from app.models.users import User, Group, user_group_association
from app.models.computers import Computer
from app.models.incidents import Event, Incident, EventType, EventSeverity, IncidentStatus, IncidentPriority

# Export all models for easy importing
__all__ = [
    # User and Group models
    "User",
    "Group", 
    "user_group_association",
    
    # Computer models
    "Computer",
    
    # Event and Incident models
    "Event",
    "Incident",
    
    # Enums
    "EventType",
    "EventSeverity", 
    "IncidentStatus",
    "IncidentPriority"
]
