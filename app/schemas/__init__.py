"""
Pydantic schemas package.

This module imports all Pydantic schemas for API request/response validation
and provides a centralized place to access all schema definitions.
"""

# User and Group schemas
from app.schemas.users import (
    UserBase, UserCreate, UserUpdate, UserResponse, UserDetailResponse, UserSummary,
    GroupBase, GroupCreate, GroupUpdate, GroupResponse, GroupDetailResponse, GroupSummary,
    GroupMembershipRequest, GroupMembershipResponse
)

# Computer schemas
from app.schemas.computers import (
    ComputerBase, ComputerCreate, ComputerUpdate, ComputerHealthUpdate,
    ComputerResponse, ComputerDetailResponse, ComputerSummary,
    ComputerAssetReport, ComputerMetrics,
    ComputerBulkUpdate, ComputerBulkResponse
)

# Event and Incident schemas
from app.schemas.incidents import (
    EventBase, EventCreate, EventUpdate, EventResponse, EventDetailResponse, EventSummary,
    IncidentBase, IncidentCreate, IncidentUpdate, IncidentStatusUpdate, IncidentAssignment,
    IncidentResponse, IncidentDetailResponse, IncidentSummary,
    EventAnalytics, IncidentAnalytics, IncidentTrend,
    EventBulkProcess, IncidentBulkUpdate, BulkOperationResponse
)

# Export all schemas
__all__ = [
    # User schemas
    "UserBase", "UserCreate", "UserUpdate", "UserResponse", "UserDetailResponse", "UserSummary",
    
    # Group schemas
    "GroupBase", "GroupCreate", "GroupUpdate", "GroupResponse", "GroupDetailResponse", "GroupSummary",
    "GroupMembershipRequest", "GroupMembershipResponse",
    
    # Computer schemas
    "ComputerBase", "ComputerCreate", "ComputerUpdate", "ComputerHealthUpdate",
    "ComputerResponse", "ComputerDetailResponse", "ComputerSummary",
    "ComputerAssetReport", "ComputerMetrics",
    "ComputerBulkUpdate", "ComputerBulkResponse",
    
    # Event schemas
    "EventBase", "EventCreate", "EventUpdate", "EventResponse", "EventDetailResponse", "EventSummary",
    
    # Incident schemas
    "IncidentBase", "IncidentCreate", "IncidentUpdate", "IncidentStatusUpdate", "IncidentAssignment",
    "IncidentResponse", "IncidentDetailResponse", "IncidentSummary",
    
    # Analytics schemas
    "EventAnalytics", "IncidentAnalytics", "IncidentTrend",
    
    # Bulk operation schemas
    "EventBulkProcess", "IncidentBulkUpdate", "BulkOperationResponse"
]
