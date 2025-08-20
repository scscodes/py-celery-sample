"""
Pydantic schemas for Event and Incident models.

This module defines request/response schemas for FastAPI endpoints
that handle event processing and incident management operations.
"""

from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Import the enums from models for validation
from app.models.incidents import EventType, EventSeverity, IncidentStatus, IncidentPriority


# Event schemas
class EventBase(BaseModel):
    """Base Event schema with common attributes."""
    event_id: str
    event_type: EventType
    severity: EventSeverity
    source: str
    title: str
    description: Optional[str] = None
    raw_data: Optional[str] = None
    occurred_at: datetime
    correlation_id: Optional[str] = None


class EventCreate(EventBase):
    """Schema for creating a new event."""
    computer_id: Optional[int] = None
    user_id: Optional[int] = None
    parent_event_id: Optional[int] = None


class EventUpdate(BaseModel):
    """Schema for updating an existing event."""
    description: Optional[str] = None
    is_processed: Optional[bool] = None
    correlation_id: Optional[str] = None


class EventResponse(EventBase):
    """Schema for event API responses."""
    id: int
    computer_id: Optional[int]
    user_id: Optional[int]
    parent_event_id: Optional[int]
    detected_at: datetime
    is_processed: bool
    processed_at: Optional[datetime]
    created_at: datetime
    
    # Computed properties
    age_hours: Optional[float] = None
    is_critical: Optional[bool] = None
    requires_immediate_attention: Optional[bool] = None
    
    class Config:
        from_attributes = True


# Incident schemas
class IncidentBase(BaseModel):
    """Base Incident schema with common attributes."""
    title: str
    description: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: IncidentPriority = IncidentPriority.MEDIUM
    impact: Optional[str] = None
    urgency: Optional[str] = None


class IncidentCreate(IncidentBase):
    """Schema for creating a new incident."""
    reporter_id: int
    assignee_id: Optional[int] = None
    assigned_group: Optional[str] = None
    affected_computer_id: Optional[int] = None
    affected_users_count: int = 1
    sla_due_date: Optional[datetime] = None


class IncidentUpdate(BaseModel):
    """Schema for updating an existing incident."""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: Optional[IncidentPriority] = None
    impact: Optional[str] = None
    urgency: Optional[str] = None
    status: Optional[IncidentStatus] = None
    assignee_id: Optional[int] = None
    assigned_group: Optional[str] = None
    resolution: Optional[str] = None
    last_update: Optional[str] = None
    public_notes: Optional[str] = None
    private_notes: Optional[str] = None
    requires_change: Optional[bool] = None
    change_request_id: Optional[str] = None


class IncidentStatusUpdate(BaseModel):
    """Schema for incident status updates."""
    status: IncidentStatus
    resolution: Optional[str] = None
    update_notes: Optional[str] = None


class IncidentAssignment(BaseModel):
    """Schema for incident assignment."""
    assignee_id: Optional[int] = None
    assigned_group: Optional[str] = None
    assignment_notes: Optional[str] = None


class IncidentResponse(IncidentBase):
    """Schema for incident API responses."""
    id: int
    ticket_id: str
    reporter_id: int
    assignee_id: Optional[int]
    assigned_group: Optional[str]
    affected_computer_id: Optional[int]
    affected_users_count: int
    status: IncidentStatus
    resolution: Optional[str]
    sla_due_date: Optional[datetime]
    sla_breached: bool
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    resolution_time_hours: Optional[float]
    requires_change: bool
    change_request_id: Optional[str]
    escalated: bool
    escalated_at: Optional[datetime]
    escalation_reason: Optional[str]
    last_update: Optional[str]
    public_notes: Optional[str]
    private_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    age_hours: Optional[float] = None
    is_overdue: Optional[bool] = None
    is_open: Optional[bool] = None
    is_high_priority: Optional[bool] = None
    
    class Config:
        from_attributes = True


# Summary schemas for references
class EventSummary(BaseModel):
    """Summary schema for event references."""
    id: int
    event_id: str
    event_type: EventType
    severity: EventSeverity
    title: str
    occurred_at: datetime
    is_processed: bool
    
    class Config:
        from_attributes = True


class IncidentSummary(BaseModel):
    """Summary schema for incident references."""
    id: int
    ticket_id: str
    title: str
    status: IncidentStatus
    priority: IncidentPriority
    created_at: datetime
    is_overdue: Optional[bool] = None
    
    class Config:
        from_attributes = True


# Extended response schemas with relationships
class EventDetailResponse(EventResponse):
    """Detailed event response including relationships."""
    computer: Optional['ComputerSummary'] = None
    user: Optional['UserSummary'] = None
    parent_event: Optional[EventSummary] = None
    child_events: List[EventSummary] = []
    
    class Config:
        from_attributes = True


class IncidentDetailResponse(IncidentResponse):
    """Detailed incident response including relationships."""
    reporter: Optional['UserSummary'] = None
    assignee: Optional['UserSummary'] = None
    affected_computer: Optional['ComputerSummary'] = None
    related_events: List[EventSummary] = []
    
    class Config:
        from_attributes = True


# Reporting and analytics schemas
class EventAnalytics(BaseModel):
    """Schema for event analytics and reporting."""
    total_events: int
    events_by_type: dict
    events_by_severity: dict
    events_by_status: dict
    critical_events: int
    unprocessed_events: int
    events_last_24h: int
    top_event_sources: List[dict]


class IncidentAnalytics(BaseModel):
    """Schema for incident analytics and reporting."""
    total_incidents: int
    open_incidents: int
    overdue_incidents: int
    incidents_by_status: dict
    incidents_by_priority: dict
    average_resolution_time: Optional[float]
    sla_breach_rate: float
    incidents_last_24h: int
    top_incident_categories: List[dict]


class IncidentTrend(BaseModel):
    """Schema for incident trend data."""
    date: datetime
    created_count: int
    resolved_count: int
    open_count: int


# Bulk operations schemas
class EventBulkProcess(BaseModel):
    """Schema for bulk event processing."""
    event_ids: List[int]
    mark_as_processed: bool = True
    correlation_id: Optional[str] = None


class IncidentBulkUpdate(BaseModel):
    """Schema for bulk incident updates."""
    incident_ids: List[int]
    updates: IncidentUpdate


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation responses."""
    processed_count: int
    failed_count: int
    errors: List[str]


# Import dependencies for type hinting
from app.schemas.users import UserSummary
from app.schemas.computers import ComputerSummary

# Update forward references
EventDetailResponse.model_rebuild()
IncidentDetailResponse.model_rebuild()
