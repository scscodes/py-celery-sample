"""
Task management API endpoints.

This module provides REST API endpoints for Celery task management,
monitoring, and direct task execution for demonstration purposes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.dependencies import get_database, get_redis_manager
from app.core.redis import RedisManager
from app.tasks.basic.cache_tasks import (
    cache_set, cache_get, cache_delete, cache_bulk_set, 
    cache_warm_up, cache_health_check
)
from app.tasks.basic.crud_tasks import (
    create_user_task, sync_computer_data_task, process_event_task,
    batch_update_computers_task, cleanup_old_events_task
)
from app.tasks.celery_app import get_registered_tasks, get_active_workers, get_task_stats

router = APIRouter()


@router.get("/")
async def list_task_types():
    """
    List all available task types and their descriptions.
    
    Returns information about all registered Celery tasks
    available for execution and monitoring.
    """
    return {
        "basic_tasks": {
            "cache_operations": {
                "cache.set_value": "Set a value in Redis cache with TTL",
                "cache.get_value": "Get a value from Redis cache",
                "cache.delete_value": "Delete a value from Redis cache",
                "cache.bulk_set": "Set multiple cache values in bulk",
                "cache.warm_up": "Warm up cache with predefined data patterns",
                "cache.health_check": "Perform Redis cache health check"
            },
            "crud_operations": {
                "crud.create_user": "Create a new user via Celery task",
                "crud.sync_computer_data": "Sync computer data from external monitoring",
                "crud.process_event": "Process and store system events",
                "crud.batch_update_computers": "Batch update multiple computers",
                "crud.cleanup_old_events": "Clean up old events from database"
            }
        },
        "orchestration_tasks": {
            "description": "Advanced Celery patterns like chains, groups, canvas workflows",
            "status": "Coming soon"
        },
        "enterprise_tasks": {
            "description": "Enterprise-specific IT operations and workflows",
            "status": "Coming soon"
        },
        "total_registered": len(get_registered_tasks())
    }


@router.get("/registered")
async def get_all_registered_tasks():
    """
    Get all registered Celery tasks.
    
    Returns complete list of tasks registered with the Celery application.
    """
    tasks = get_registered_tasks()
    
    return {
        "registered_tasks": tasks,
        "task_count": len(tasks),
        "categories": {
            "cache": [task for task in tasks if "cache" in task],
            "crud": [task for task in tasks if "crud" in task],
            "orchestration": [task for task in tasks if "orchestration" in task],
            "enterprise": [task for task in tasks if "enterprise" in task],
            "system": [task for task in tasks if task.startswith("celery.")]
        }
    }


@router.get("/workers")
async def get_worker_status():
    """
    Get status of active Celery workers.
    
    Returns information about active workers, their queues,
    and current task execution status.
    """
    try:
        active_workers = get_active_workers()
        task_stats = get_task_stats()
        
        return {
            "active_workers": active_workers,
            "worker_stats": task_stats,
            "worker_count": len(active_workers) if active_workers else 0,
            "status": "connected" if active_workers else "no_workers"
        }
    except Exception as e:
        return {
            "active_workers": None,
            "worker_stats": None,
            "worker_count": 0,
            "status": "connection_failed",
            "error": str(e)
        }


# Cache task endpoints
@router.post("/cache/set")
async def execute_cache_set(
    key: str,
    value: Any,
    ttl: int = Query(3600, description="Time to live in seconds")
):
    """
    Execute cache set task.
    
    Sets a value in Redis cache using Celery task execution.
    """
    task_result = cache_set.delay(key, value, ttl)
    
    return {
        "task_id": task_result.id,
        "task_name": "cache.set_value",
        "status": "submitted",
        "parameters": {
            "key": key,
            "value": value,
            "ttl": ttl
        }
    }


@router.post("/cache/get")
async def execute_cache_get(key: str):
    """
    Execute cache get task.
    
    Retrieves a value from Redis cache using Celery task execution.
    """
    task_result = cache_get.delay(key)
    
    return {
        "task_id": task_result.id,
        "task_name": "cache.get_value",
        "status": "submitted",
        "parameters": {
            "key": key
        }
    }


@router.post("/cache/delete")
async def execute_cache_delete(key: str):
    """
    Execute cache delete task.
    
    Deletes a value from Redis cache using Celery task execution.
    """
    task_result = cache_delete.delay(key)
    
    return {
        "task_id": task_result.id,
        "task_name": "cache.delete_value",
        "status": "submitted",
        "parameters": {
            "key": key
        }
    }


@router.post("/cache/bulk-set")
async def execute_cache_bulk_set(
    items: List[Dict[str, Any]],
    default_ttl: int = Query(3600, description="Default TTL for items without specific TTL")
):
    """
    Execute bulk cache set task.
    
    Sets multiple values in Redis cache using Celery task execution.
    """
    task_result = cache_bulk_set.delay(items, default_ttl)
    
    return {
        "task_id": task_result.id,
        "task_name": "cache.bulk_set",
        "status": "submitted",
        "parameters": {
            "item_count": len(items),
            "default_ttl": default_ttl
        }
    }


@router.post("/cache/warm-up")
async def execute_cache_warm_up(cache_patterns: List[Dict[str, Any]]):
    """
    Execute cache warm-up task.
    
    Warms up cache with predefined data patterns using Celery task.
    """
    task_result = cache_warm_up.delay(cache_patterns)
    
    return {
        "task_id": task_result.id,
        "task_name": "cache.warm_up",
        "status": "submitted",
        "parameters": {
            "pattern_count": len(cache_patterns)
        }
    }


@router.post("/cache/health-check")
async def execute_cache_health_check():
    """
    Execute cache health check task.
    
    Performs comprehensive Redis health check using Celery task.
    """
    task_result = cache_health_check.delay()
    
    return {
        "task_id": task_result.id,
        "task_name": "cache.health_check",
        "status": "submitted",
        "parameters": {}
    }


# CRUD task endpoints
@router.post("/crud/create-user")
async def execute_create_user(user_data: Dict[str, Any]):
    """
    Execute user creation task.
    
    Creates a new user using Celery task execution.
    """
    task_result = create_user_task.delay(user_data)
    
    return {
        "task_id": task_result.id,
        "task_name": "crud.create_user",
        "status": "submitted",
        "parameters": {
            "username": user_data.get("username"),
            "email": user_data.get("email")
        }
    }


@router.post("/crud/sync-computer")
async def execute_sync_computer(computer_data: Dict[str, Any]):
    """
    Execute computer data sync task.
    
    Syncs computer data from external monitoring using Celery task.
    """
    task_result = sync_computer_data_task.delay(computer_data)
    
    return {
        "task_id": task_result.id,
        "task_name": "crud.sync_computer_data",
        "status": "submitted",
        "parameters": {
            "hostname": computer_data.get("hostname")
        }
    }


@router.post("/crud/process-event")
async def execute_process_event(event_data: Dict[str, Any]):
    """
    Execute event processing task.
    
    Processes and stores system events using Celery task.
    """
    task_result = process_event_task.delay(event_data)
    
    return {
        "task_id": task_result.id,
        "task_name": "crud.process_event",
        "status": "submitted",
        "parameters": {
            "event_id": event_data.get("event_id"),
            "event_type": event_data.get("event_type"),
            "severity": event_data.get("severity")
        }
    }


@router.post("/crud/batch-update-computers")
async def execute_batch_update_computers(computer_updates: List[Dict[str, Any]]):
    """
    Execute batch computer update task.
    
    Updates multiple computers efficiently using Celery task.
    """
    task_result = batch_update_computers_task.delay(computer_updates)
    
    return {
        "task_id": task_result.id,
        "task_name": "crud.batch_update_computers",
        "status": "submitted",
        "parameters": {
            "computer_count": len(computer_updates)
        }
    }


@router.post("/crud/cleanup-events")
async def execute_cleanup_events(days_to_keep: int = Query(90, description="Number of days to keep events")):
    """
    Execute event cleanup task.
    
    Cleans up old events from the database using Celery task.
    """
    task_result = cleanup_old_events_task.delay(days_to_keep)
    
    return {
        "task_id": task_result.id,
        "task_name": "crud.cleanup_old_events",
        "status": "submitted",
        "parameters": {
            "days_to_keep": days_to_keep
        }
    }


# Task result endpoints
@router.get("/result/{task_id}")
async def get_task_result(task_id: str):
    """
    Get result of a specific task.
    
    Retrieves the result, status, and metadata for a Celery task.
    """
    from app.tasks.celery_app import celery_app
    
    try:
        result = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result,
            "successful": result.successful(),
            "failed": result.failed(),
            "ready": result.ready(),
            "info": result.info,
            "traceback": result.traceback if result.failed() else None,
            "date_done": str(result.date_done) if result.date_done else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving task result: {str(e)}"
        )


@router.post("/result/{task_id}/revoke")
async def revoke_task(
    task_id: str,
    terminate: bool = Query(False, description="Whether to terminate the task if already running")
):
    """
    Revoke (cancel) a specific task.
    
    Cancels a pending or running Celery task.
    """
    from app.tasks.celery_app import celery_app
    
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        
        return {
            "task_id": task_id,
            "revoked": True,
            "terminated": terminate,
            "message": f"Task {task_id} has been {'terminated' if terminate else 'revoked'}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error revoking task: {str(e)}"
        )


# Demonstration endpoints
@router.post("/demo/workflow")
async def execute_demo_workflow():
    """
    Execute a demonstration workflow.
    
    Runs a series of connected tasks to showcase Celery capabilities.
    """
    # Simple workflow: Health check -> Cache operations -> Data sync
    
    # Step 1: Health check
    health_task = cache_health_check.delay()
    
    # Step 2: Cache some demo data
    demo_cache_data = [
        {"key": "demo:user:1", "value": {"name": "Demo User", "status": "active"}, "ttl": 300},
        {"key": "demo:system:status", "value": "operational", "ttl": 300},
        {"key": "demo:timestamp", "value": datetime.now().isoformat(), "ttl": 300}
    ]
    cache_task = cache_bulk_set.delay(demo_cache_data)
    
    # Step 3: Demo computer sync
    demo_computer = {
        "hostname": f"demo-computer-{datetime.now().strftime('%H%M%S')}",
        "status": "active",
        "health_status": "healthy",
        "cpu_usage_percent": 25.5,
        "memory_usage_percent": 45.2,
        "disk_usage_percent": 60.8,
        "is_online": True
    }
    sync_task = sync_computer_data_task.delay(demo_computer)
    
    return {
        "workflow_id": f"demo_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "Demonstration workflow showcasing basic Celery operations",
        "tasks": [
            {
                "step": 1,
                "task_id": health_task.id,
                "name": "cache_health_check",
                "description": "Verify Redis cache connectivity"
            },
            {
                "step": 2,
                "task_id": cache_task.id,
                "name": "cache_bulk_set",
                "description": "Cache demonstration data"
            },
            {
                "step": 3,
                "task_id": sync_task.id,
                "name": "sync_computer_data",
                "description": "Sync demonstration computer data"
            }
        ],
        "execution_time": datetime.now().isoformat(),
        "note": "Use GET /tasks/result/{task_id} to check individual task results"
    }
