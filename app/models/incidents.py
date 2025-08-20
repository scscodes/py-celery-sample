"""
Event and Incident SQLAlchemy models.

This module defines database models for system events,
incident tracking, and IT service management workflows.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.core.database import Base


class EventType(enum.Enum):
    """Enumeration for different types of system events."""
    SYSTEM = "system"
    SECURITY = "security"
    NETWORK = "network"
    APPLICATION = "application"
    USER = "user"
    HARDWARE = "hardware"
    AUDIT = "audit"


class EventSeverity(enum.Enum):
    """Enumeration for event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IncidentStatus(enum.Enum):
    """Enumeration for incident status values."""
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class IncidentPriority(enum.Enum):
    """Enumeration for incident priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class Event(Base):
    """
    Event model representing system events and log entries.
    
    Captures various types of events from systems, applications,
    and user activities for monitoring and audit purposes.
    """
    __tablename__ = "events"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)  # External event ID
    
    # Event classification
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    severity = Column(SQLEnum(EventSeverity), nullable=False, index=True)
    source = Column(String(200), nullable=False)  # Source system/application
    
    # Event content
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    raw_data = Column(Text, nullable=True)  # Original event data (JSON)
    
    # Context and relationships
    computer_id = Column(Integer, ForeignKey('computers.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # User associated with event
    
    # Event details
    occurred_at = Column(DateTime, nullable=False, index=True)
    detected_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Correlation and grouping
    correlation_id = Column(String(100), nullable=True, index=True)  # Group related events
    parent_event_id = Column(Integer, ForeignKey('events.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    computer = relationship("Computer", back_populates="events")
    user = relationship("User")
    
    # Self-referential for event chains
    child_events = relationship("Event", remote_side=[id])
    
    # Note: Event-Incident relationships would require an association table
    # For now, incidents can reference events but not vice versa
    
    def __repr__(self):
        return f"<Event(id='{self.event_id}', type='{self.event_type.value}', severity='{self.severity.value}')>"
    
    @property
    def age_hours(self):
        """Get age of event in hours."""
        return (datetime.utcnow() - self.occurred_at).total_seconds() / 3600
    
    @property
    def is_critical(self):
        """Check if event is critical severity."""
        return self.severity == EventSeverity.CRITICAL
    
    @property
    def requires_immediate_attention(self):
        """Check if event requires immediate attention."""
        return (
            self.severity in [EventSeverity.CRITICAL, EventSeverity.ERROR] and
            not self.is_processed
        )


class Incident(Base):
    """
    Incident model representing IT service management incidents.
    
    Tracks IT incidents from creation through resolution,
    including assignment, escalation, and change management.
    """
    __tablename__ = "incidents"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, index=True, nullable=False)  # INC-123456
    
    # Incident classification
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)  # Hardware, Software, Network, etc.
    subcategory = Column(String(100), nullable=True)
    
    # Priority and impact
    priority = Column(SQLEnum(IncidentPriority), nullable=False, default=IncidentPriority.MEDIUM)
    impact = Column(String(50), nullable=True)  # High, Medium, Low
    urgency = Column(String(50), nullable=True)  # High, Medium, Low
    
    # Status and workflow
    status = Column(SQLEnum(IncidentStatus), nullable=False, default=IncidentStatus.NEW, index=True)
    resolution = Column(Text, nullable=True)
    
    # Assignment and ownership
    reporter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    assignee_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    assigned_group = Column(String(100), nullable=True)
    
    # Affected resources
    affected_computer_id = Column(Integer, ForeignKey('computers.id'), nullable=True)
    affected_users_count = Column(Integer, default=1, nullable=False)
    
    # Service Level Agreement (SLA)
    sla_due_date = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, default=False, nullable=False)
    
    # Resolution tracking
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    resolution_time_hours = Column(Float, nullable=True)
    
    # Change management
    requires_change = Column(Boolean, default=False, nullable=False)
    change_request_id = Column(String(50), nullable=True)
    
    # Escalation
    escalated = Column(Boolean, default=False, nullable=False)
    escalated_at = Column(DateTime, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    
    # Communication and updates
    last_update = Column(Text, nullable=True)
    public_notes = Column(Text, nullable=True)  # Visible to end users
    private_notes = Column(Text, nullable=True)  # Internal notes only
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reported_incidents")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_incidents")
    affected_computer = relationship("Computer", back_populates="incidents")
    
    # Note: For full event-incident relationships, would need association table
    # For now, incidents can reference specific events through descriptions
    
    def __repr__(self):
        return f"<Incident(ticket_id='{self.ticket_id}', status='{self.status.value}', priority='{self.priority.value}')>"
    
    @property
    def age_hours(self):
        """Get age of incident in hours."""
        return (datetime.utcnow() - self.created_at).total_seconds() / 3600
    
    @property
    def is_overdue(self):
        """Check if incident is past SLA due date."""
        if not self.sla_due_date:
            return False
        return datetime.utcnow() > self.sla_due_date and self.status not in [
            IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.CANCELLED
        ]
    
    @property
    def is_open(self):
        """Check if incident is in an open state."""
        return self.status not in [
            IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.CANCELLED
        ]
    
    @property
    def is_high_priority(self):
        """Check if incident is high priority."""
        return self.priority in [IncidentPriority.HIGH, IncidentPriority.URGENT, IncidentPriority.CRITICAL]
    
    def calculate_resolution_time(self):
        """Calculate and update resolution time if incident is resolved."""
        if self.resolved_at and self.created_at:
            delta = self.resolved_at - self.created_at
            self.resolution_time_hours = delta.total_seconds() / 3600
