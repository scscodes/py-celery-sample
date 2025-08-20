"""
Basic CRUD operations with Celery and SQLAlchemy.

This module demonstrates fundamental database operations executed
as Celery tasks, showcasing database integration patterns.
"""

from celery import shared_task
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from app.core.database import SessionLocal
from app.core.redis import redis_manager
from app.models import User, Group, Computer, Event, Incident


def get_db_session() -> Session:
    """Get database session for tasks."""
    return SessionLocal()


@shared_task(bind=True, name="crud.create_user")
def create_user_task(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user via Celery task.
    
    This task demonstrates database creation operations with
    error handling and cache invalidation patterns.
    
    Args:
        user_data: Dictionary containing user information
        
    Returns:
        Dict containing creation result and user information
    """
    db = get_db_session()
    try:
        start_time = datetime.utcnow()
        
        # Create new user instance
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            display_name=user_data.get('display_name'),
            department=user_data.get('department'),
            title=user_data.get('title'),
            employee_id=user_data.get('employee_id'),
            phone=user_data.get('phone'),
            office_location=user_data.get('office_location'),
            manager_id=user_data.get('manager_id'),
            is_active=user_data.get('is_active', True)
        )
        
        # Add to database session
        db.add(user)
        db.commit()
        db.refresh(user)
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Invalidate related cache entries
        cache_keys_to_invalidate = [
            f"user_list",
            f"department_users_{user.department}",
            f"active_users"
        ]
        
        for cache_key in cache_keys_to_invalidate:
            redis_manager.delete(cache_key)
        
        result = {
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "department": user.department
            },
            "operation_time_ms": operation_time_ms,
            "cache_invalidated": cache_keys_to_invalidate,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        print(f"👤 User CREATED: {user.username} (ID: {user.id}, Time: {operation_time_ms:.2f}ms)")
        
        return result
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = f"Database error creating user: {str(e)}"
        print(f"💥 User CREATE failed: {error_msg}")
        raise self.retry(exc=e, countdown=60, max_retries=3)
        
    except Exception as e:
        db.rollback()
        error_msg = f"Unexpected error creating user: {str(e)}"
        print(f"💥 User CREATE failed: {error_msg}")
        raise
        
    finally:
        db.close()


@shared_task(bind=True, name="crud.sync_computer_data")
def sync_computer_data_task(self, computer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync computer data from external monitoring systems.
    
    This task demonstrates upsert operations (update or create)
    commonly used for asset synchronization.
    
    Args:
        computer_data: Dictionary containing computer information
        
    Returns:
        Dict containing sync result and computer information
    """
    db = get_db_session()
    try:
        start_time = datetime.utcnow()
        
        hostname = computer_data['hostname']
        
        # Try to find existing computer
        computer = db.query(Computer).filter(Computer.hostname == hostname).first()
        
        if computer:
            # Update existing computer
            for key, value in computer_data.items():
                if hasattr(computer, key) and value is not None:
                    setattr(computer, key, value)
            
            computer.updated_at = datetime.utcnow()
            operation_type = "updated"
            
        else:
            # Create new computer
            computer = Computer(**computer_data)
            db.add(computer)
            operation_type = "created"
        
        # Update health status based on metrics if provided
        if all(k in computer_data for k in ['cpu_usage_percent', 'memory_usage_percent', 'disk_usage_percent']):
            computer.update_health_metrics(
                computer_data['cpu_usage_percent'],
                computer_data['memory_usage_percent'],
                computer_data['disk_usage_percent']
            )
        
        db.commit()
        db.refresh(computer)
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Update cache with fresh computer data
        cache_key = f"computer_{computer.hostname}"
        computer_cache_data = {
            "id": computer.id,
            "hostname": computer.hostname,
            "status": computer.status,
            "health_status": computer.health_status,
            "is_online": computer.is_online,
            "last_seen": computer.last_seen.isoformat() if computer.last_seen else None,
            "owner_name": computer.owner_name,
            "department": computer.department
        }
        redis_manager.set(cache_key, computer_cache_data, 1800)  # Cache for 30 minutes
        
        # Invalidate list caches
        redis_manager.delete("computer_list")
        redis_manager.delete(f"department_computers_{computer.department}")
        
        result = {
            "success": True,
            "operation": operation_type,
            "computer": {
                "id": computer.id,
                "hostname": computer.hostname,
                "status": computer.status,
                "health_status": computer.health_status,
                "is_online": computer.is_online,
                "needs_attention": computer.needs_attention
            },
            "operation_time_ms": operation_time_ms,
            "cached": True,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        print(f"💻 Computer {operation_type.upper()}: {hostname} (Health: {computer.health_status}, Time: {operation_time_ms:.2f}ms)")
        
        return result
        
    except SQLAlchemyError as e:
        db.rollback()
        print(f"💥 Computer SYNC failed for {computer_data.get('hostname', 'unknown')}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)
        
    except Exception as e:
        db.rollback()
        print(f"💥 Computer SYNC error: {str(e)}")
        raise
        
    finally:
        db.close()


@shared_task(bind=True, name="crud.process_event")
def process_event_task(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and store system events.
    
    This task demonstrates event processing patterns including
    correlation, deduplication, and automated incident creation.
    
    Args:
        event_data: Dictionary containing event information
        
    Returns:
        Dict containing processing result
    """
    db = get_db_session()
    try:
        start_time = datetime.utcnow()
        
        # Check for duplicate events (based on event_id)
        existing_event = db.query(Event).filter(Event.event_id == event_data['event_id']).first()
        
        if existing_event:
            # Update processed timestamp if not already processed
            if not existing_event.is_processed:
                existing_event.is_processed = True
                existing_event.processed_at = datetime.utcnow()
                db.commit()
            
            result = {
                "success": True,
                "operation": "duplicate_updated",
                "event_id": existing_event.event_id,
                "message": "Event already exists, updated processing status"
            }
            
            print(f"🔄 Event DUPLICATE: {event_data['event_id']} (updated processing status)")
            return result
        
        # Create new event
        event = Event(
            event_id=event_data['event_id'],
            event_type=event_data['event_type'],
            severity=event_data['severity'],
            source=event_data['source'],
            title=event_data['title'],
            description=event_data.get('description'),
            raw_data=json.dumps(event_data.get('raw_data', {})),
            occurred_at=datetime.fromisoformat(event_data['occurred_at']),
            computer_id=event_data.get('computer_id'),
            user_id=event_data.get('user_id'),
            correlation_id=event_data.get('correlation_id'),
            parent_event_id=event_data.get('parent_event_id')
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        # Check if event should trigger incident creation
        should_create_incident = (
            event.severity in ['error', 'critical'] and
            event.event_type in ['system', 'hardware', 'security']
        )
        
        incident_created = False
        incident_id = None
        
        if should_create_incident:
            # Create incident for critical events
            incident = Incident(
                ticket_id=f"AUTO-{event.id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                title=f"Auto-generated: {event.title}",
                description=f"Automatically created from event {event.event_id}\\n\\n{event.description}",
                category="System",
                priority="high" if event.severity == "critical" else "medium",
                status="new",
                reporter_id=1,  # System user - should be configurable
                affected_computer_id=event.computer_id,
                affected_users_count=1
            )
            
            db.add(incident)
            db.commit()
            db.refresh(incident)
            
            incident_created = True
            incident_id = incident.id
            
            print(f"🚨 Auto-created incident {incident.ticket_id} for critical event {event.event_id}")
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Cache recent events for quick access
        recent_events_key = f"recent_events_{event.source}"
        cached_events = redis_manager.get(recent_events_key) or []
        
        # Add current event to cache (keep last 100 events)
        cached_events.insert(0, {
            "id": event.id,
            "event_id": event.event_id,
            "severity": event.severity.value,
            "title": event.title,
            "occurred_at": event.occurred_at.isoformat()
        })
        cached_events = cached_events[:100]  # Keep only recent 100 events
        
        redis_manager.set(recent_events_key, cached_events, 3600)  # Cache for 1 hour
        
        result = {
            "success": True,
            "operation": "created",
            "event": {
                "id": event.id,
                "event_id": event.event_id,
                "severity": event.severity.value,
                "title": event.title,
                "requires_attention": event.requires_immediate_attention
            },
            "incident_created": incident_created,
            "incident_id": incident_id,
            "operation_time_ms": operation_time_ms,
            "cached": True,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        severity_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}
        emoji = severity_emoji.get(event.severity.value, "📝")
        print(f"{emoji} Event PROCESSED: {event.event_id} ({event.severity.value}, Time: {operation_time_ms:.2f}ms)")
        
        return result
        
    except SQLAlchemyError as e:
        db.rollback()
        print(f"💥 Event PROCESS failed for {event_data.get('event_id', 'unknown')}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)
        
    except Exception as e:
        db.rollback()
        print(f"💥 Event PROCESS error: {str(e)}")
        raise
        
    finally:
        db.close()


@shared_task(bind=True, name="crud.batch_update_computers")
def batch_update_computers_task(self, computer_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Batch update multiple computers efficiently.
    
    This task demonstrates bulk operations and transaction management
    for high-performance data updates.
    
    Args:
        computer_updates: List of computer update dictionaries
        
    Returns:
        Dict containing batch update results
    """
    db = get_db_session()
    try:
        start_time = datetime.utcnow()
        
        updated_count = 0
        failed_count = 0
        errors = []
        updated_hostnames = []
        
        for update_data in computer_updates:
            try:
                # Support both hostname and computer_id as identifiers
                computer = None
                identifier = None
                
                if 'hostname' in update_data:
                    identifier = update_data['hostname']
                    computer = db.query(Computer).filter(Computer.hostname == identifier).first()
                elif 'computer_id' in update_data:
                    identifier = update_data['computer_id']
                    computer = db.query(Computer).filter(Computer.id == identifier).first()
                else:
                    failed_count += 1
                    errors.append("Update failed: missing 'hostname' or 'computer_id' identifier")
                    continue
                
                if computer:
                    # Apply updates
                    for key, value in update_data.items():
                        if hasattr(computer, key) and key not in ['hostname', 'computer_id', 'id']:
                            setattr(computer, key, value)
                    
                    computer.updated_at = datetime.utcnow()
                    updated_count += 1
                    updated_hostnames.append(computer.hostname)  # Always use hostname for tracking
                    
                else:
                    failed_count += 1
                    errors.append(f"Computer not found: {identifier}")
                    
            except Exception as update_error:
                failed_count += 1
                identifier_value = update_data.get('hostname') or update_data.get('computer_id', 'unknown')
                errors.append(f"Update failed for {identifier_value}: {str(update_error)}")
        
        # Commit all updates at once
        if updated_count > 0:
            db.commit()
            
            # Invalidate cache for updated computers
            for hostname in updated_hostnames:
                redis_manager.delete(f"computer_{hostname}")
            
            # Invalidate list caches
            redis_manager.delete("computer_list")
            redis_manager.delete("computer_health_summary")
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        result = {
            "success": True,
            "total_updates": len(computer_updates),
            "updated_count": updated_count,
            "failed_count": failed_count,
            "updated_hostnames": updated_hostnames,
            "errors": errors,
            "operation_time_ms": operation_time_ms,
            "avg_time_per_update_ms": operation_time_ms / len(computer_updates) if computer_updates else 0,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        print(f"📦 Batch UPDATE: {updated_count} computers updated, {failed_count} failed (Time: {operation_time_ms:.2f}ms)")
        
        return result
        
    except SQLAlchemyError as e:
        db.rollback()
        print(f"💥 Batch UPDATE failed: {str(e)}")
        raise self.retry(exc=e, countdown=120, max_retries=2)
        
    except Exception as e:
        db.rollback()
        print(f"💥 Batch UPDATE error: {str(e)}")
        raise
        
    finally:
        db.close()


@shared_task(bind=True, name="crud.cleanup_old_events")
def cleanup_old_events_task(self, days_to_keep: int = 90) -> Dict[str, Any]:
    """
    Clean up old events from the database.
    
    This task demonstrates maintenance operations and data lifecycle management.
    
    Args:
        days_to_keep: Number of days to keep events (default: 90)
        
    Returns:
        Dict containing cleanup results
    """
    db = get_db_session()
    try:
        start_time = datetime.utcnow()
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Find old events to delete
        old_events = db.query(Event).filter(
            Event.occurred_at < cutoff_date,
            Event.is_processed == True  # Only delete processed events
        )
        
        # Count before deletion
        events_to_delete = old_events.count()
        
        if events_to_delete > 0:
            # Delete old events
            old_events.delete(synchronize_session=False)
            db.commit()
            
            # Clear related caches
            redis_manager.delete("event_statistics")
            redis_manager.delete("event_summary")
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        result = {
            "success": True,
            "days_to_keep": days_to_keep,
            "cutoff_date": cutoff_date.isoformat(),
            "events_deleted": events_to_delete,
            "operation_time_ms": operation_time_ms,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        print(f"🧹 Event CLEANUP: {events_to_delete} old events deleted (cutoff: {days_to_keep} days, Time: {operation_time_ms:.2f}ms)")
        
        return result
        
    except SQLAlchemyError as e:
        db.rollback()
        print(f"💥 Event CLEANUP failed: {str(e)}")
        raise self.retry(exc=e, countdown=300, max_retries=2)
        
    except Exception as e:
        db.rollback()
        print(f"💥 Event CLEANUP error: {str(e)}")
        raise
        
    finally:
        db.close()
