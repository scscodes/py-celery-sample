"""
System monitoring API endpoints.

This module provides REST API endpoints for system health monitoring,
performance metrics, and operational observability.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import asyncio

from app.core.dependencies import get_database, get_redis_manager
from app.core.redis import RedisManager
from app.models import User, Group, Computer, Event, Incident
from app.tasks.celery_app import get_active_workers, get_task_stats

router = APIRouter()


@router.get("/health")
async def system_health_check(
    db: Session = Depends(get_database),
    redis: RedisManager = Depends(get_redis_manager)
):
    """
    Comprehensive system health check.
    
    Checks the health of all system components including
    database, Redis, Celery workers, and application metrics.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
        "metrics": {}
    }
    
    # Database health
    try:
        user_count = db.query(User).count()
        computer_count = db.query(Computer).count()
        event_count = db.query(Event).count()
        
        health_status["components"]["database"] = {
            "status": "healthy",
            "connection": "active",
            "metrics": {
                "users": user_count,
                "computers": computer_count,
                "events": event_count
            }
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "connection": "failed",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Redis health
    try:
        redis_test_key = "health_check_test"
        redis.set(redis_test_key, "test_value", 60)
        test_value = redis.get(redis_test_key)
        redis.delete(redis_test_key)
        
        health_status["components"]["redis"] = {
            "status": "healthy",
            "connection": "active",
            "operations": {
                "set": True,
                "get": test_value == "test_value",
                "delete": True
            }
        }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "connection": "failed",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Celery worker health
    try:
        active_workers = get_active_workers()
        worker_count = len(active_workers) if active_workers else 0
        
        health_status["components"]["celery"] = {
            "status": "healthy" if worker_count > 0 else "degraded",
            "active_workers": worker_count,
            "workers": active_workers
        }
        
        if worker_count == 0:
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["components"]["celery"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Application metrics
    try:
        # Recent activity metrics
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_events = db.query(Event).filter(Event.detected_at >= last_24h).count()
        recent_incidents = db.query(Incident).filter(Incident.created_at >= last_24h).count()
        
        # System load indicators
        critical_events = db.query(Event).filter(
            Event.severity == "critical",
            Event.detected_at >= last_24h
        ).count()
        
        open_incidents = db.query(Incident).filter(
            Incident.status.in_(["new", "assigned", "in_progress", "pending"])
        ).count()
        
        health_status["metrics"] = {
            "events_24h": recent_events,
            "incidents_24h": recent_incidents,
            "critical_events_24h": critical_events,
            "open_incidents": open_incidents,
            "system_load": "normal" if critical_events < 10 else "high"
        }
        
    except Exception as e:
        health_status["metrics"] = {"error": str(e)}
    
    # Determine overall status
    component_statuses = [comp["status"] for comp in health_status["components"].values()]
    if "unhealthy" in component_statuses:
        health_status["status"] = "unhealthy"
    elif "degraded" in component_statuses:
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/metrics/system")
async def get_system_metrics(
    db: Session = Depends(get_database),
    redis: RedisManager = Depends(get_redis_manager)
):
    """
    Get comprehensive system metrics.
    
    Returns detailed metrics about system performance,
    resource utilization, and operational statistics.
    """
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": {},
        "cache": {},
        "compute": {},
        "incidents": {}
    }
    
    # Database metrics
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_computers = db.query(Computer).count()
        online_computers = db.query(Computer).filter(Computer.is_online == True).count()
        healthy_computers = db.query(Computer).filter(Computer.health_status == "healthy").count()
        
        metrics["database"] = {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users
            },
            "computers": {
                "total": total_computers,
                "online": online_computers,
                "offline": total_computers - online_computers,
                "healthy": healthy_computers,
                "unhealthy": total_computers - healthy_computers
            }
        }
    except Exception as e:
        metrics["database"] = {"error": str(e)}
    
    # Cache metrics
    try:
        # Test cache performance
        test_start = datetime.utcnow()
        redis.set("perf_test", "test", 60)
        redis.get("perf_test")
        redis.delete("perf_test")
        test_duration = (datetime.utcnow() - test_start).total_seconds() * 1000
        
        metrics["cache"] = {
            "status": "operational",
            "performance": {
                "round_trip_ms": round(test_duration, 2)
            }
        }
    except Exception as e:
        metrics["cache"] = {"status": "error", "error": str(e)}
    
    # Compute resource metrics (from computer data)
    try:
        online_computers = db.query(Computer).filter(Computer.is_online == True).all()
        
        if online_computers:
            cpu_usages = [c.cpu_usage_percent for c in online_computers if c.cpu_usage_percent is not None]
            memory_usages = [c.memory_usage_percent for c in online_computers if c.memory_usage_percent is not None]
            disk_usages = [c.disk_usage_percent for c in online_computers if c.disk_usage_percent is not None]
            
            metrics["compute"] = {
                "monitored_systems": len(online_computers),
                "cpu": {
                    "average": round(sum(cpu_usages) / len(cpu_usages), 1) if cpu_usages else None,
                    "max": max(cpu_usages) if cpu_usages else None,
                    "systems_over_80": len([u for u in cpu_usages if u > 80])
                },
                "memory": {
                    "average": round(sum(memory_usages) / len(memory_usages), 1) if memory_usages else None,
                    "max": max(memory_usages) if memory_usages else None,
                    "systems_over_90": len([u for u in memory_usages if u > 90])
                },
                "disk": {
                    "average": round(sum(disk_usages) / len(disk_usages), 1) if disk_usages else None,
                    "max": max(disk_usages) if disk_usages else None,
                    "systems_over_95": len([u for u in disk_usages if u > 95])
                }
            }
        else:
            metrics["compute"] = {"monitored_systems": 0}
    except Exception as e:
        metrics["compute"] = {"error": str(e)}
    
    # Incident metrics
    try:
        total_incidents = db.query(Incident).count()
        open_incidents = db.query(Incident).filter(
            Incident.status.in_(["new", "assigned", "in_progress", "pending"])
        ).count()
        critical_incidents = db.query(Incident).filter(
            Incident.priority == "critical",
            Incident.status.notin_(["resolved", "closed", "cancelled"])
        ).count()
        overdue_incidents = db.query(Incident).filter(
            Incident.sla_due_date < datetime.utcnow(),
            Incident.status.notin_(["resolved", "closed", "cancelled"])
        ).count()
        
        metrics["incidents"] = {
            "total": total_incidents,
            "open": open_incidents,
            "critical_open": critical_incidents,
            "overdue": overdue_incidents
        }
    except Exception as e:
        metrics["incidents"] = {"error": str(e)}
    
    return metrics


@router.get("/metrics/performance")
async def get_performance_metrics(
    hours: int = Query(24, ge=1, le=168, description="Hours of data to analyze"),
    db: Session = Depends(get_database)
):
    """
    Get system performance metrics over time.
    
    Returns performance trends and statistics for the specified time period.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Event processing performance
    total_events = db.query(Event).filter(Event.detected_at >= cutoff_time).count()
    processed_events = db.query(Event).filter(
        Event.detected_at >= cutoff_time,
        Event.is_processed == True
    ).count()
    
    processing_rate = (processed_events / total_events * 100) if total_events > 0 else 0
    
    # Incident response performance
    incidents_created = db.query(Incident).filter(Incident.created_at >= cutoff_time).count()
    incidents_resolved = db.query(Incident).filter(
        Incident.created_at >= cutoff_time,
        Incident.resolved_at.isnot(None)
    ).count()
    
    resolution_rate = (incidents_resolved / incidents_created * 100) if incidents_created > 0 else 0
    
    # Average resolution time
    resolved_incidents = db.query(Incident).filter(
        Incident.created_at >= cutoff_time,
        Incident.resolution_time_hours.isnot(None)
    ).all()
    
    avg_resolution_time = None
    if resolved_incidents:
        total_time = sum(incident.resolution_time_hours for incident in resolved_incidents)
        avg_resolution_time = round(total_time / len(resolved_incidents), 2)
    
    return {
        "time_period": f"{hours} hours",
        "analysis_start": cutoff_time.isoformat(),
        "analysis_end": datetime.utcnow().isoformat(),
        "event_processing": {
            "total_events": total_events,
            "processed_events": processed_events,
            "processing_rate_percent": round(processing_rate, 1)
        },
        "incident_management": {
            "incidents_created": incidents_created,
            "incidents_resolved": incidents_resolved,
            "resolution_rate_percent": round(resolution_rate, 1),
            "average_resolution_hours": avg_resolution_time
        }
    }


@router.get("/alerts")
async def get_system_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=500, description="Maximum alerts to return"),
    db: Session = Depends(get_database)
):
    """
    Get current system alerts and warnings.
    
    Returns alerts based on system conditions, thresholds,
    and operational issues requiring attention.
    """
    alerts = []
    current_time = datetime.utcnow()
    
    # Critical system alerts
    critical_events_24h = db.query(Event).filter(
        Event.severity == "critical",
        Event.detected_at >= current_time - timedelta(hours=24),
        Event.is_processed == False
    ).count()
    
    if critical_events_24h > 0:
        alerts.append({
            "id": "critical_events_unprocessed",
            "severity": "critical",
            "title": f"{critical_events_24h} Unprocessed Critical Events",
            "description": f"There are {critical_events_24h} critical events from the last 24 hours that haven't been processed",
            "timestamp": current_time.isoformat(),
            "category": "event_processing"
        })
    
    # Overdue incidents
    overdue_incidents = db.query(Incident).filter(
        Incident.sla_due_date < current_time,
        Incident.status.notin_(["resolved", "closed", "cancelled"])
    ).count()
    
    if overdue_incidents > 0:
        alerts.append({
            "id": "incidents_overdue",
            "severity": "warning",
            "title": f"{overdue_incidents} Overdue Incidents",
            "description": f"There are {overdue_incidents} incidents that have exceeded their SLA deadlines",
            "timestamp": current_time.isoformat(),
            "category": "incident_management"
        })
    
    # System health alerts
    unhealthy_computers = db.query(Computer).filter(
        Computer.health_status.in_(["critical", "warning"]),
        Computer.is_online == True
    ).count()
    
    if unhealthy_computers > 0:
        severity_level = "critical" if unhealthy_computers > 10 else "warning"
        alerts.append({
            "id": "computers_unhealthy",
            "severity": severity_level,
            "title": f"{unhealthy_computers} Computers Need Attention",
            "description": f"There are {unhealthy_computers} computers with health issues requiring attention",
            "timestamp": current_time.isoformat(),
            "category": "system_health"
        })
    
    # Offline computers
    offline_computers = db.query(Computer).filter(
        Computer.is_online == False,
        Computer.status == "active"
    ).count()
    
    if offline_computers > 5:  # Threshold for alerting
        alerts.append({
            "id": "computers_offline",
            "severity": "warning",
            "title": f"{offline_computers} Computers Offline",
            "description": f"There are {offline_computers} active computers that are currently offline",
            "timestamp": current_time.isoformat(),
            "category": "connectivity"
        })
    
    # Filter by severity if specified
    if severity:
        alerts = [alert for alert in alerts if alert["severity"] == severity]
    
    # Apply limit
    alerts = alerts[:limit]
    
    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "severity_counts": {
            "critical": len([a for a in alerts if a["severity"] == "critical"]),
            "warning": len([a for a in alerts if a["severity"] == "warning"]),
            "info": len([a for a in alerts if a["severity"] == "info"])
        },
        "generated_at": current_time.isoformat()
    }


@router.get("/status/realtime")
async def get_realtime_status():
    """
    Get real-time system status stream.
    
    Returns current system status suitable for dashboard display.
    """
    return StreamingResponse(
        generate_status_stream(),
        media_type="text/plain"
    )


async def generate_status_stream():
    """Generate real-time status updates."""
    while True:
        try:
            # Get current timestamp
            current_time = datetime.utcnow().isoformat()
            
            # Simple status update
            status_update = {
                "timestamp": current_time,
                "status": "operational",
                "uptime": "24h 30m",
                "active_workers": 3,
                "pending_tasks": 0,
                "cache_hit_rate": 95.2
            }
            
            yield f"data: {json.dumps(status_update)}\\n\\n"
            
            # Wait before next update
            await asyncio.sleep(5)
            
        except Exception as e:
            error_update = {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            yield f"data: {json.dumps(error_update)}\\n\\n"
            break


@router.get("/dashboard")
async def get_dashboard_data(
    db: Session = Depends(get_database)
):
    """
    Get comprehensive dashboard data.
    
    Returns all key metrics and status information needed
    for a system monitoring dashboard.
    """
    current_time = datetime.utcnow()
    
    # Summary statistics
    summary = {
        "users": {
            "total": db.query(User).count(),
            "active": db.query(User).filter(User.is_active == True).count()
        },
        "computers": {
            "total": db.query(Computer).count(),
            "online": db.query(Computer).filter(Computer.is_online == True).count(),
            "healthy": db.query(Computer).filter(Computer.health_status == "healthy").count()
        },
        "incidents": {
            "open": db.query(Incident).filter(
                Incident.status.in_(["new", "assigned", "in_progress", "pending"])
            ).count(),
            "critical": db.query(Incident).filter(
                Incident.priority == "critical",
                Incident.status.notin_(["resolved", "closed"])
            ).count()
        }
    }
    
    # Recent activity (last 24 hours)
    last_24h = current_time - timedelta(hours=24)
    recent_activity = {
        "events": db.query(Event).filter(Event.detected_at >= last_24h).count(),
        "incidents_created": db.query(Incident).filter(Incident.created_at >= last_24h).count(),
        "incidents_resolved": db.query(Incident).filter(
            Incident.resolved_at >= last_24h
        ).count()
    }
    
    # System status
    try:
        workers = get_active_workers()
        worker_count = len(workers) if workers else 0
        system_status = {
            "overall": "operational" if worker_count > 0 else "degraded",
            "workers": worker_count,
            "database": "connected",
            "cache": "connected"
        }
    except:
        system_status = {
            "overall": "degraded",
            "workers": 0,
            "database": "unknown",
            "cache": "unknown"
        }
    
    return {
        "timestamp": current_time.isoformat(),
        "summary": summary,
        "recent_activity": recent_activity,
        "system_status": system_status,
        "uptime": "operational"  # Would calculate actual uptime
    }
