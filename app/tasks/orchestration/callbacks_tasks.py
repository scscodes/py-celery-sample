"""
Success/failure callbacks and cleanup task patterns.

This module provides comprehensive callback mechanisms for task lifecycle management,
including success callbacks, failure handlers, cleanup tasks, and notification systems.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta
import json
import random
import time
from dataclasses import dataclass
from enum import Enum

from celery import signature, chain, group
from celery.signals import task_success, task_failure, task_retry
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class CallbackType(Enum):
    """Types of callbacks available."""
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    CLEANUP = "cleanup"
    NOTIFICATION = "notification"
    AUDIT = "audit"


@dataclass
class CallbackConfig:
    """Configuration for task callbacks."""
    success_callbacks: List[str] = None
    failure_callbacks: List[str] = None
    cleanup_callbacks: List[str] = None
    always_callbacks: List[str] = None
    notification_channels: List[str] = None
    audit_enabled: bool = True
    cleanup_delay_seconds: int = 300  # 5 minutes default
    
    def __post_init__(self):
        # Initialize lists if None
        for attr in ['success_callbacks', 'failure_callbacks', 'cleanup_callbacks', 
                    'always_callbacks', 'notification_channels']:
            if getattr(self, attr) is None:
                setattr(self, attr, [])


# =============================================================================
# CALLBACK DECORATORS AND UTILITIES
# =============================================================================

def with_callbacks(callback_config: CallbackConfig):
    """Decorator to add callback support to Celery tasks."""
    def decorator(task_func):
        def wrapper(self, *args, **kwargs):
            task_id = self.request.id
            task_name = task_func.__name__
            
            logger.info(f"[{task_id}] Starting {task_name} with callbacks enabled")
            
            start_time = datetime.utcnow()
            task_context = {
                "task_id": task_id,
                "task_name": task_name,
                "args": args,
                "kwargs": kwargs,
                "start_time": start_time.isoformat()
            }
            
            try:
                # Execute the main task
                result = task_func(self, *args, **kwargs)
                
                # Task succeeded - execute success callbacks
                end_time = datetime.utcnow()
                task_context.update({
                    "result": result,
                    "end_time": end_time.isoformat(),
                    "duration_seconds": (end_time - start_time).total_seconds(),
                    "status": "success"
                })
                
                # Execute success callbacks asynchronously
                for callback_name in callback_config.success_callbacks:
                    execute_callback.delay(callback_name, CallbackType.SUCCESS.value, task_context)
                
                # Execute audit logging if enabled
                if callback_config.audit_enabled:
                    audit_task_execution.delay(task_context)
                
                # Execute notification callbacks
                for channel in callback_config.notification_channels:
                    send_task_notification.delay(channel, "success", task_context)
                
                logger.info(f"[{task_id}] {task_name} completed successfully with callbacks")
                return result
                
            except Exception as exc:
                # Task failed - execute failure callbacks
                end_time = datetime.utcnow()
                task_context.update({
                    "error": str(exc),
                    "exception_type": exc.__class__.__name__,
                    "end_time": end_time.isoformat(),
                    "duration_seconds": (end_time - start_time).total_seconds(),
                    "status": "failed"
                })
                
                # Execute failure callbacks asynchronously
                for callback_name in callback_config.failure_callbacks:
                    execute_callback.delay(callback_name, CallbackType.FAILURE.value, task_context)
                
                # Execute audit logging if enabled
                if callback_config.audit_enabled:
                    audit_task_execution.delay(task_context)
                
                # Execute notification callbacks for failures
                for channel in callback_config.notification_channels:
                    send_task_notification.delay(channel, "failure", task_context)
                
                logger.error(f"[{task_id}] {task_name} failed with callbacks: {exc}")
                raise exc
                
            finally:
                # Always execute cleanup callbacks with delay
                if callback_config.cleanup_callbacks:
                    schedule_cleanup_callbacks.apply_async(
                        args=[callback_config.cleanup_callbacks, task_context],
                        countdown=callback_config.cleanup_delay_seconds
                    )
                
                # Execute always callbacks
                for callback_name in callback_config.always_callbacks:
                    execute_callback.delay(callback_name, CallbackType.ALWAYS.value, task_context)
        
        return wrapper
    return decorator


# =============================================================================
# CORE CALLBACK TASKS
# =============================================================================

@celery_app.task(bind=True, name="callbacks.execute_callback")
def execute_callback(self, callback_name: str, callback_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a specific callback function."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Executing {callback_type} callback: {callback_name}")
    
    callback_start = datetime.utcnow()
    
    try:
        # Route to specific callback implementations
        if callback_name == "log_success":
            result = log_success_callback(context)
        elif callback_name == "log_failure":
            result = log_failure_callback(context)
        elif callback_name == "update_metrics":
            result = update_metrics_callback(context)
        elif callback_name == "send_email":
            result = send_email_callback(context)
        elif callback_name == "send_slack":
            result = send_slack_callback(context)
        elif callback_name == "update_database":
            result = update_database_callback(context)
        elif callback_name == "generate_report":
            result = generate_report_callback(context)
        elif callback_name == "cleanup_temp_files":
            result = cleanup_temp_files_callback(context)
        elif callback_name == "release_resources":
            result = release_resources_callback(context)
        else:
            # Generic callback execution
            result = generic_callback(callback_name, context)
        
        callback_end = datetime.utcnow()
        execution_result = {
            "callback_name": callback_name,
            "callback_type": callback_type,
            "status": "success",
            "result": result,
            "execution_time_seconds": (callback_end - callback_start).total_seconds(),
            "executed_at": callback_end.isoformat(),
            "executor_task_id": task_id
        }
        
        logger.info(f"[{task_id}] Callback {callback_name} executed successfully")
        return execution_result
        
    except Exception as exc:
        callback_end = datetime.utcnow()
        execution_result = {
            "callback_name": callback_name,
            "callback_type": callback_type,
            "status": "failed",
            "error": str(exc),
            "execution_time_seconds": (callback_end - callback_start).total_seconds(),
            "executed_at": callback_end.isoformat(),
            "executor_task_id": task_id
        }
        
        logger.error(f"[{task_id}] Callback {callback_name} failed: {exc}")
        return execution_result


@celery_app.task(bind=True, name="callbacks.schedule_cleanup_callbacks")
def schedule_cleanup_callbacks(self, callback_names: List[str], context: Dict[str, Any]) -> List[str]:
    """Schedule cleanup callbacks to run after a delay."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Scheduling cleanup callbacks: {callback_names}")
    
    cleanup_task_ids = []
    
    for callback_name in callback_names:
        cleanup_task = execute_callback.delay(callback_name, CallbackType.CLEANUP.value, context)
        cleanup_task_ids.append(cleanup_task.id)
        logger.info(f"[{task_id}] Scheduled cleanup callback {callback_name}: {cleanup_task.id}")
    
    return cleanup_task_ids


# =============================================================================
# SPECIFIC CALLBACK IMPLEMENTATIONS
# =============================================================================

def log_success_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Log successful task execution."""
    logger.info(f"SUCCESS CALLBACK: Task {context['task_name']} ({context['task_id']}) completed successfully")
    
    return {
        "callback_type": "log_success",
        "message": f"Task {context['task_name']} completed successfully",
        "duration": context.get("duration_seconds", 0),
        "logged_at": datetime.utcnow().isoformat()
    }


def log_failure_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Log failed task execution."""
    error = context.get("error", "Unknown error")
    logger.error(f"FAILURE CALLBACK: Task {context['task_name']} ({context['task_id']}) failed: {error}")
    
    return {
        "callback_type": "log_failure",
        "message": f"Task {context['task_name']} failed: {error}",
        "error_type": context.get("exception_type", "Unknown"),
        "duration": context.get("duration_seconds", 0),
        "logged_at": datetime.utcnow().isoformat()
    }


def update_metrics_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Update application metrics."""
    # Simulate metrics update
    time.sleep(0.1)
    
    metrics_update = {
        "callback_type": "update_metrics",
        "task_name": context["task_name"],
        "status": context["status"],
        "duration": context.get("duration_seconds", 0),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # In production, send to metrics system (Prometheus, DataDog, etc.)
    logger.info(f"METRICS CALLBACK: Updated metrics for {context['task_name']}")
    
    return metrics_update


def send_email_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Send email notification."""
    # Simulate email sending
    time.sleep(random.uniform(0.2, 0.5))
    
    email_config = {
        "to": ["admin@example.com", "ops@example.com"],
        "subject": f"Task {context['task_name']} - {context['status'].upper()}",
        "body": f"Task {context['task_id']} has {context['status']}.\nDuration: {context.get('duration_seconds', 0):.1f}s",
        "sent_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"EMAIL CALLBACK: Sent notification for {context['task_name']}")
    
    return {
        "callback_type": "send_email",
        "email_config": email_config,
        "delivery_status": "sent"
    }


def send_slack_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Send Slack notification."""
    # Simulate Slack API call
    time.sleep(random.uniform(0.1, 0.3))
    
    status_emoji = "✅" if context["status"] == "success" else "❌"
    message = f"{status_emoji} Task `{context['task_name']}` {context['status']} in {context.get('duration_seconds', 0):.1f}s"
    
    slack_config = {
        "channel": "#operations",
        "message": message,
        "task_id": context["task_id"],
        "sent_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"SLACK CALLBACK: Sent notification for {context['task_name']}")
    
    return {
        "callback_type": "send_slack",
        "slack_config": slack_config,
        "delivery_status": "sent"
    }


def update_database_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Update database with task execution results."""
    # Simulate database update
    time.sleep(random.uniform(0.1, 0.4))
    
    db_record = {
        "task_id": context["task_id"],
        "task_name": context["task_name"],
        "status": context["status"],
        "start_time": context["start_time"],
        "end_time": context["end_time"],
        "duration_seconds": context.get("duration_seconds", 0),
        "error_message": context.get("error"),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"DATABASE CALLBACK: Updated record for {context['task_name']}")
    
    return {
        "callback_type": "update_database",
        "record_id": f"task_record_{random.randint(1000, 9999)}",
        "db_record": db_record
    }


def generate_report_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate execution report."""
    # Simulate report generation
    time.sleep(random.uniform(0.3, 0.8))
    
    report = {
        "report_id": f"report_{random.randint(10000, 99999)}",
        "task_summary": {
            "task_id": context["task_id"],
            "task_name": context["task_name"],
            "status": context["status"],
            "execution_time": context.get("duration_seconds", 0),
            "success_rate": 100 if context["status"] == "success" else 0
        },
        "generated_at": datetime.utcnow().isoformat(),
        "report_format": "json"
    }
    
    logger.info(f"REPORT CALLBACK: Generated report for {context['task_name']}")
    
    return {
        "callback_type": "generate_report",
        "report": report
    }


def cleanup_temp_files_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Clean up temporary files created during task execution."""
    # Simulate file cleanup
    time.sleep(random.uniform(0.1, 0.3))
    
    temp_files = [
        f"/tmp/task_{context['task_id']}_data.tmp",
        f"/tmp/task_{context['task_id']}_cache.tmp",
        f"/tmp/task_{context['task_id']}_logs.tmp"
    ]
    
    cleanup_result = {
        "callback_type": "cleanup_temp_files",
        "files_cleaned": temp_files,
        "cleanup_status": "success",
        "space_freed_mb": random.uniform(10, 100),
        "cleaned_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"CLEANUP CALLBACK: Cleaned up temp files for {context['task_name']}")
    
    return cleanup_result


def release_resources_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Release allocated resources (connections, locks, etc.)."""
    # Simulate resource release
    time.sleep(random.uniform(0.05, 0.2))
    
    resources_released = [
        f"database_connection_{context['task_id']}",
        f"cache_lock_{context['task_id']}",
        f"memory_pool_{context['task_id']}"
    ]
    
    resource_result = {
        "callback_type": "release_resources",
        "resources_released": resources_released,
        "release_status": "success",
        "released_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"RESOURCE CALLBACK: Released resources for {context['task_name']}")
    
    return resource_result


def generic_callback(callback_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generic callback for custom implementations."""
    # Simulate generic callback processing
    time.sleep(random.uniform(0.1, 0.5))
    
    return {
        "callback_type": "generic",
        "callback_name": callback_name,
        "context_keys": list(context.keys()),
        "processed_at": datetime.utcnow().isoformat(),
        "message": f"Generic callback {callback_name} executed"
    }


# =============================================================================
# NOTIFICATION AND AUDIT TASKS
# =============================================================================

@celery_app.task(bind=True, name="callbacks.send_task_notification")
def send_task_notification(self, channel: str, event_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Send task event notifications through various channels."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Sending {event_type} notification via {channel}")
    
    # Route to specific notification channels
    if channel == "email":
        result = send_email_callback(context)
    elif channel == "slack":
        result = send_slack_callback(context)
    elif channel == "webhook":
        result = send_webhook_notification(context)
    elif channel == "sms":
        result = send_sms_notification(context)
    else:
        result = {
            "channel": channel,
            "status": "unsupported",
            "message": f"Notification channel {channel} not supported"
        }
    
    logger.info(f"[{task_id}] Notification sent via {channel}")
    return result


def send_webhook_notification(context: Dict[str, Any]) -> Dict[str, Any]:
    """Send webhook notification."""
    # Simulate webhook call
    time.sleep(random.uniform(0.2, 0.6))
    
    webhook_payload = {
        "event": "task_completed",
        "task_id": context["task_id"],
        "task_name": context["task_name"],
        "status": context["status"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {
        "callback_type": "webhook",
        "webhook_url": "https://api.example.com/webhooks/tasks",
        "payload": webhook_payload,
        "response_status": 200,
        "sent_at": datetime.utcnow().isoformat()
    }


def send_sms_notification(context: Dict[str, Any]) -> Dict[str, Any]:
    """Send SMS notification for critical events."""
    # Simulate SMS sending
    time.sleep(random.uniform(0.3, 0.8))
    
    message = f"ALERT: Task {context['task_name']} {context['status']} at {datetime.utcnow().strftime('%H:%M')}"
    
    return {
        "callback_type": "sms",
        "recipient": "+1-555-0123",
        "message": message,
        "delivery_status": "sent",
        "sent_at": datetime.utcnow().isoformat()
    }


@celery_app.task(bind=True, name="callbacks.audit_task_execution")
def audit_task_execution(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """Create audit trail for task execution."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Creating audit trail for {context['task_name']}")
    
    # Simulate audit logging
    time.sleep(random.uniform(0.1, 0.3))
    
    audit_record = {
        "audit_id": f"audit_{random.randint(100000, 999999)}",
        "event_type": "task_execution",
        "task_id": context["task_id"],
        "task_name": context["task_name"],
        "status": context["status"],
        "start_time": context["start_time"],
        "end_time": context["end_time"],
        "duration_seconds": context.get("duration_seconds", 0),
        "user_id": context.get("user_id", "system"),
        "ip_address": context.get("ip_address", "127.0.0.1"),
        "metadata": {
            "args_count": len(context.get("args", [])),
            "kwargs_count": len(context.get("kwargs", {})),
            "error_type": context.get("exception_type") if context["status"] == "failed" else None
        },
        "audit_timestamp": datetime.utcnow().isoformat(),
        "auditor_task_id": task_id
    }
    
    # In production, save to audit database or log system
    logger.info(f"[{task_id}] Audit record created: {audit_record['audit_id']}")
    
    return audit_record


# =============================================================================
# CALLBACK ORCHESTRATION TASKS
# =============================================================================

@celery_app.task(bind=True, name="callbacks.batch_callback_executor")
def batch_callback_executor(self, callback_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute multiple callbacks in batch for efficiency."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Executing batch of {len(callback_batch)} callbacks")
    
    batch_results = []
    
    for callback_info in callback_batch:
        try:
            result = execute_callback.apply_async([
                callback_info["callback_name"],
                callback_info["callback_type"],
                callback_info["context"]
            ]).get()
            
            batch_results.append({
                "callback_info": callback_info,
                "result": result,
                "status": "success"
            })
            
        except Exception as exc:
            batch_results.append({
                "callback_info": callback_info,
                "error": str(exc),
                "status": "failed"
            })
    
    success_count = sum(1 for r in batch_results if r["status"] == "success")
    
    logger.info(f"[{task_id}] Batch callback execution complete: {success_count}/{len(callback_batch)} successful")
    
    return {
        "batch_id": f"batch_{task_id}",
        "total_callbacks": len(callback_batch),
        "successful_callbacks": success_count,
        "failed_callbacks": len(callback_batch) - success_count,
        "results": batch_results,
        "executed_at": datetime.utcnow().isoformat()
    }


# =============================================================================
# CALLBACK-ENABLED EXAMPLE TASKS
# =============================================================================

@celery_app.task(bind=True, name="callbacks.example_task_with_callbacks")
@with_callbacks(CallbackConfig(
    success_callbacks=["log_success", "update_metrics", "send_email"],
    failure_callbacks=["log_failure", "update_metrics", "send_slack"],
    cleanup_callbacks=["cleanup_temp_files", "release_resources"],
    notification_channels=["email", "slack"],
    audit_enabled=True
))
def example_task_with_callbacks(self, data: Dict[str, Any], processing_options: Dict[str, Any]) -> Dict[str, Any]:
    """Example task demonstrating comprehensive callback usage."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Executing example task with comprehensive callbacks")
    
    # Simulate task processing
    processing_time = processing_options.get("processing_time", 2.0)
    time.sleep(random.uniform(processing_time * 0.5, processing_time * 1.5))
    
    # Simulate potential failure
    failure_rate = processing_options.get("failure_rate", 0.1)
    if random.random() < failure_rate:
        raise Exception("Simulated task failure for callback demonstration")
    
    # Return success result
    result = {
        "task_id": task_id,
        "data_processed": data,
        "processing_options": processing_options,
        "items_processed": random.randint(100, 1000),
        "processing_duration": processing_time,
        "completed_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"[{task_id}] Example task completed successfully")
    return result
