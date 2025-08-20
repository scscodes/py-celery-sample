"""
Incident and Event management API endpoints.

This module provides REST API endpoints for incident tracking,
event processing, and IT service management workflows.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.dependencies import get_database
from app.schemas.incidents import (
    EventCreate, EventUpdate, EventResponse, EventDetailResponse,
    IncidentCreate, IncidentUpdate, IncidentStatusUpdate, IncidentAssignment,
    IncidentResponse, IncidentDetailResponse,
    EventAnalytics, IncidentAnalytics, IncidentTrend,
    EventBulkProcess, IncidentBulkUpdate, BulkOperationResponse
)
from app.models.incidents import Event, Incident, EventType, EventSeverity, IncidentStatus, IncidentPriority
from app.tasks.basic.crud_tasks import process_event_task

router = APIRouter()


# Event endpoints
@router.get("/events", response_model=List[EventResponse])
async def list_events(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    severity: Optional[EventSeverity] = Query(None, description="Filter by severity"),
    is_processed: Optional[bool] = Query(None, description="Filter by processing status"),
    computer_id: Optional[int] = Query(None, description="Filter by computer ID"),
    hours_ago: Optional[int] = Query(None, description="Filter events from last N hours"),
    db: Session = Depends(get_database)
):
    """
    Retrieve a list of events with optional filtering.
    
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return (1-1000)
    - **event_type**: Filter by event type (system, security, network, etc.)
    - **severity**: Filter by severity (info, warning, error, critical)
    - **is_processed**: Filter by processing status
    - **computer_id**: Filter events from specific computer
    - **hours_ago**: Filter events from last N hours
    """
    query = db.query(Event)
    
    # Apply filters
    if event_type:
        query = query.filter(Event.event_type == event_type)
    if severity:
        query = query.filter(Event.severity == severity)
    if is_processed is not None:
        query = query.filter(Event.is_processed == is_processed)
    if computer_id:
        query = query.filter(Event.computer_id == computer_id)
    if hours_ago:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_ago)
        query = query.filter(Event.occurred_at >= cutoff_time)
    
    # Apply pagination and ordering
    events = query.order_by(Event.occurred_at.desc()).offset(skip).limit(limit).all()
    
    return events


@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: int,
    db: Session = Depends(get_database)
):
    """
    Retrieve a specific event by ID with detailed information.
    """
    event = db.query(Event).options(
        joinedload(Event.computer),  # Load computer relationship
        joinedload(Event.user),      # Load user relationship
        joinedload(Event.child_events)  # Load child events
        # Note: parent_event relationship removed - not defined in model
    ).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    
    return event


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_database)
):
    """
    Create a new event.
    
    Processes incoming events and triggers background tasks
    for analysis, correlation, and incident creation.
    """
    # Check if event_id already exists
    existing_event = db.query(Event).filter(Event.event_id == event_data.event_id).first()
    if existing_event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event with ID '{event_data.event_id}' already exists"
        )
    
    # Create event
    event = Event(**event_data.dict())
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Trigger async event processing
    process_event_task.delay(event_data.dict())
    
    return event


@router.put("/events/{event_id}/process", response_model=EventResponse)
async def process_event(
    event_id: int,
    db: Session = Depends(get_database)
):
    """
    Mark an event as processed.
    
    Updates the event processing status and timestamp.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    
    event.is_processed = True
    event.processed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(event)
    
    return event


# Incident endpoints
@router.get("/incidents", response_model=List[IncidentResponse])
async def list_incidents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status_filter: Optional[IncidentStatus] = Query(None, alias="status", description="Filter by status"),
    priority: Optional[IncidentPriority] = Query(None, description="Filter by priority"),
    assignee_id: Optional[int] = Query(None, description="Filter by assignee"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_overdue: Optional[bool] = Query(None, description="Filter overdue incidents"),
    days_ago: Optional[int] = Query(None, description="Filter incidents from last N days"),
    db: Session = Depends(get_database)
):
    """
    Retrieve a list of incidents with optional filtering.
    
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return (1-1000)
    - **status**: Filter by incident status
    - **priority**: Filter by priority level
    - **assignee_id**: Filter by assigned user
    - **category**: Filter by incident category
    - **is_overdue**: Filter overdue incidents
    - **days_ago**: Filter incidents from last N days
    """
    query = db.query(Incident)
    
    # Apply filters
    if status_filter:
        query = query.filter(Incident.status == status_filter)
    if priority:
        query = query.filter(Incident.priority == priority)
    if assignee_id:
        query = query.filter(Incident.assignee_id == assignee_id)
    if category:
        query = query.filter(Incident.category == category)
    if is_overdue is not None:
        if is_overdue:
            query = query.filter(
                Incident.sla_due_date < datetime.utcnow(),
                Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.CANCELLED])
            )
        else:
            query = query.filter(
                (Incident.sla_due_date >= datetime.utcnow()) | (Incident.sla_due_date.is_(None))
            )
    if days_ago:
        cutoff_date = datetime.utcnow() - timedelta(days=days_ago)
        query = query.filter(Incident.created_at >= cutoff_date)
    
    # Apply pagination and ordering
    incidents = query.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()
    
    return incidents


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: int,
    db: Session = Depends(get_database)
):
    """
    Retrieve a specific incident by ID with detailed information.
    """
    incident = db.query(Incident).options(
        joinedload(Incident.reporter),         # Load reporter relationship
        joinedload(Incident.assignee),         # Load assignee relationship
        joinedload(Incident.affected_computer)  # Load affected computer relationship
        # Note: related_events relationship removed - not defined in model
    ).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found"
        )
    
    return incident


@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident_data: IncidentCreate,
    db: Session = Depends(get_database)
):
    """
    Create a new incident.
    
    Creates a new IT service management incident and triggers
    background tasks for assignment and notification.
    """
    # Generate ticket ID
    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
    ticket_count = db.query(Incident).count() + 1
    ticket_id = f"INC-{timestamp}-{ticket_count:04d}"
    
    # Create incident
    incident = Incident(
        ticket_id=ticket_id,
        **incident_data.dict()
    )
    
    db.add(incident)
    db.commit()
    db.refresh(incident)
    
    return incident


@router.put("/incidents/{incident_id}/status", response_model=IncidentResponse)
async def update_incident_status(
    incident_id: int,
    status_data: IncidentStatusUpdate,
    db: Session = Depends(get_database)
):
    """
    Update incident status.
    
    Updates incident status and triggers workflow actions
    based on the new status.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found"
        )
    
    # Update status
    incident.status = status_data.status
    
    # Handle status-specific updates
    if status_data.status == IncidentStatus.RESOLVED:
        incident.resolved_at = datetime.utcnow()
        incident.resolution = status_data.resolution
        incident.calculate_resolution_time()
    elif status_data.status == IncidentStatus.CLOSED:
        if not incident.resolved_at:
            incident.resolved_at = datetime.utcnow()
            incident.calculate_resolution_time()
        incident.closed_at = datetime.utcnow()
    
    # Add update notes
    if status_data.update_notes:
        incident.last_update = status_data.update_notes
    
    db.commit()
    db.refresh(incident)
    
    return incident


@router.put("/incidents/{incident_id}/assign", response_model=IncidentResponse)
async def assign_incident(
    incident_id: int,
    assignment_data: IncidentAssignment,
    db: Session = Depends(get_database)
):
    """
    Assign incident to user or group.
    
    Updates incident assignment and triggers notification workflows.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found"
        )
    
    # Update assignment
    incident.assignee_id = assignment_data.assignee_id
    incident.assigned_group = assignment_data.assigned_group
    
    # Update status if currently new
    if incident.status == IncidentStatus.NEW:
        incident.status = IncidentStatus.ASSIGNED
    
    # Add assignment notes
    if assignment_data.assignment_notes:
        incident.last_update = assignment_data.assignment_notes
    
    db.commit()
    db.refresh(incident)
    
    return incident


@router.get("/analytics/events", response_model=EventAnalytics)
async def get_event_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_database)
):
    """
    Get event analytics and statistics.
    
    Returns comprehensive analytics for events over the specified period.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    total_events = db.query(Event).filter(Event.occurred_at >= cutoff_date).count()
    critical_events = db.query(Event).filter(
        Event.occurred_at >= cutoff_date,
        Event.severity == EventSeverity.CRITICAL
    ).count()
    unprocessed_events = db.query(Event).filter(
        Event.occurred_at >= cutoff_date,
        Event.is_processed == False
    ).count()
    events_last_24h = db.query(Event).filter(
        Event.occurred_at >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    # Additional analytics would be calculated here
    return {
        "total_events": total_events,
        "events_by_type": {},  # Would be populated with actual data
        "events_by_severity": {},
        "events_by_status": {},
        "critical_events": critical_events,
        "unprocessed_events": unprocessed_events,
        "events_last_24h": events_last_24h,
        "top_event_sources": []
    }


@router.get("/analytics/incidents", response_model=IncidentAnalytics)
async def get_incident_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_database)
):
    """
    Get incident analytics and statistics.
    
    Returns comprehensive analytics for incidents over the specified period.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    total_incidents = db.query(Incident).filter(Incident.created_at >= cutoff_date).count()
    open_incidents = db.query(Incident).filter(
        Incident.created_at >= cutoff_date,
        Incident.status.in_([IncidentStatus.NEW, IncidentStatus.ASSIGNED, IncidentStatus.IN_PROGRESS, IncidentStatus.PENDING])
    ).count()
    overdue_incidents = db.query(Incident).filter(
        Incident.created_at >= cutoff_date,
        Incident.sla_due_date < datetime.utcnow(),
        Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.CANCELLED])
    ).count()
    incidents_last_24h = db.query(Incident).filter(
        Incident.created_at >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    # Calculate average resolution time
    resolved_incidents = db.query(Incident).filter(
        Incident.created_at >= cutoff_date,
        Incident.resolution_time_hours.isnot(None)
    ).all()
    
    avg_resolution_time = None
    if resolved_incidents:
        total_time = sum(incident.resolution_time_hours for incident in resolved_incidents)
        avg_resolution_time = total_time / len(resolved_incidents)
    
    # Calculate SLA breach rate
    sla_total = db.query(Incident).filter(
        Incident.created_at >= cutoff_date,
        Incident.sla_due_date.isnot(None)
    ).count()
    sla_breached = db.query(Incident).filter(
        Incident.created_at >= cutoff_date,
        Incident.sla_breached == True
    ).count()
    sla_breach_rate = (sla_breached / sla_total * 100) if sla_total > 0 else 0
    
    return {
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "overdue_incidents": overdue_incidents,
        "incidents_by_status": {},  # Would be populated with actual data
        "incidents_by_priority": {},
        "average_resolution_time": avg_resolution_time,
        "sla_breach_rate": sla_breach_rate,
        "incidents_last_24h": incidents_last_24h,
        "top_incident_categories": []
    }
