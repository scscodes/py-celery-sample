"""
Priority-based task execution and queue management.

This module provides sophisticated priority queue management with SLA guarantees,
resource allocation, queue balancing, and priority-based routing.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import json
import random
import time
import heapq
from dataclasses import dataclass, field
from enum import Enum

from celery import signature, group, chain
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Standard priority levels."""
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BULK = 10


class QueueType(Enum):
    """Different queue types for priority management."""
    REAL_TIME = "real_time"        # <1s SLA
    INTERACTIVE = "interactive"     # <5s SLA
    BACKGROUND = "background"       # <30s SLA
    BATCH = "batch"                # <5min SLA
    BULK = "bulk"                  # Best effort


@dataclass
class PriorityTaskConfig:
    """Configuration for priority-based task execution."""
    priority: int = Priority.NORMAL.value
    queue_type: QueueType = QueueType.BACKGROUND
    sla_seconds: Optional[float] = None
    max_retries: int = 3
    timeout_seconds: Optional[float] = None
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    
    def __post_init__(self):
        # Set default SLA based on queue type if not specified
        if self.sla_seconds is None:
            sla_mapping = {
                QueueType.REAL_TIME: 1.0,
                QueueType.INTERACTIVE: 5.0,
                QueueType.BACKGROUND: 30.0,
                QueueType.BATCH: 300.0,
                QueueType.BULK: None  # Best effort
            }
            self.sla_seconds = sla_mapping[self.queue_type]


@dataclass
class TaskExecution:
    """Track task execution metrics for priority analysis."""
    task_id: str
    task_name: str
    priority: int
    queue_type: QueueType
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "queued"
    sla_target: Optional[float] = None
    actual_duration: Optional[float] = None
    
    @property
    def waiting_time(self) -> Optional[float]:
        """Time spent waiting in queue before execution."""
        if self.started_at:
            return (self.started_at - self.submitted_at).total_seconds()
        return None
    
    @property
    def total_time(self) -> Optional[float]:
        """Total time from submission to completion."""
        if self.completed_at:
            return (self.completed_at - self.submitted_at).total_seconds()
        return None
    
    @property
    def sla_met(self) -> Optional[bool]:
        """Whether SLA was met."""
        if self.sla_target and self.total_time:
            return self.total_time <= self.sla_target
        return None


# Global task execution tracking (in production, use Redis or database)
_task_executions: Dict[str, TaskExecution] = {}


# =============================================================================
# PRIORITY QUEUE MANAGEMENT
# =============================================================================

@celery_app.task(bind=True, name="priority.submit_priority_task")
def submit_priority_task(self, task_name: str, task_args: List[Any], task_kwargs: Dict[str, Any], 
                        config: Dict[str, Any]) -> Dict[str, Any]:
    """Submit a task with priority configuration."""
    scheduler_task_id = self.request.id
    priority_config = PriorityTaskConfig(**config)
    
    logger.info(f"[{scheduler_task_id}] Submitting priority task: {task_name} (priority: {priority_config.priority})")
    
    # Create task execution record
    submission_time = datetime.utcnow()
    
    # Route task based on priority and queue type
    queue_name = get_queue_for_priority(priority_config.priority, priority_config.queue_type)
    
    # Create task signature with routing
    task_signature = signature(
        task_name,
        args=task_args,
        kwargs=task_kwargs,
        queue=queue_name,
        priority=priority_config.priority,
        countdown=0 if priority_config.priority >= Priority.HIGH.value else random.uniform(0, 1)
    )
    
    # Set task options based on configuration
    if priority_config.timeout_seconds:
        task_signature.set(time_limit=priority_config.timeout_seconds)
    
    if priority_config.max_retries:
        task_signature.set(retry=True, max_retries=priority_config.max_retries)
    
    # Execute the task
    task_result = task_signature.apply_async()
    
    # Track execution
    execution = TaskExecution(
        task_id=task_result.id,
        task_name=task_name,
        priority=priority_config.priority,
        queue_type=priority_config.queue_type,
        submitted_at=submission_time,
        sla_target=priority_config.sla_seconds
    )
    
    _task_executions[task_result.id] = execution
    
    # Schedule SLA monitoring
    if priority_config.sla_seconds:
        monitor_task_sla.apply_async(
            args=[task_result.id, priority_config.sla_seconds],
            countdown=priority_config.sla_seconds + 5  # Check 5 seconds after SLA
        )
    
    submission_result = {
        "task_id": task_result.id,
        "scheduler_task_id": scheduler_task_id,
        "priority": priority_config.priority,
        "queue_type": priority_config.queue_type.value,
        "queue_name": queue_name,
        "sla_seconds": priority_config.sla_seconds,
        "submitted_at": submission_time.isoformat(),
        "estimated_start_time": estimate_start_time(priority_config).isoformat()
    }
    
    logger.info(f"[{scheduler_task_id}] Priority task submitted: {task_result.id} -> {queue_name}")
    return submission_result


def get_queue_for_priority(priority: int, queue_type: QueueType) -> str:
    """Determine appropriate queue based on priority and type."""
    if priority >= Priority.CRITICAL.value:
        return "critical_priority"
    elif priority >= Priority.HIGH.value:
        return "high_priority"
    elif queue_type == QueueType.REAL_TIME:
        return "real_time"
    elif queue_type == QueueType.INTERACTIVE:
        return "interactive"
    elif queue_type == QueueType.BATCH:
        return "batch_processing"
    elif queue_type == QueueType.BULK:
        return "bulk_processing"
    else:
        return "default"


def estimate_start_time(config: PriorityTaskConfig) -> datetime:
    """Estimate when task will start based on current queue load."""
    # Simulate queue load analysis
    base_delay = {
        QueueType.REAL_TIME: 0.1,
        QueueType.INTERACTIVE: 0.5,
        QueueType.BACKGROUND: 2.0,
        QueueType.BATCH: 10.0,
        QueueType.BULK: 60.0
    }.get(config.queue_type, 5.0)
    
    # Adjust for priority
    if config.priority >= Priority.CRITICAL.value:
        priority_factor = 0.1
    elif config.priority >= Priority.HIGH.value:
        priority_factor = 0.3
    elif config.priority >= Priority.NORMAL.value:
        priority_factor = 1.0
    else:
        priority_factor = 2.0
    
    estimated_delay = base_delay * priority_factor * random.uniform(0.8, 1.2)
    return datetime.utcnow() + timedelta(seconds=estimated_delay)


# =============================================================================
# SLA MONITORING AND ENFORCEMENT
# =============================================================================

@celery_app.task(bind=True, name="priority.monitor_task_sla")
def monitor_task_sla(self, monitored_task_id: str, sla_seconds: float) -> Dict[str, Any]:
    """Monitor task SLA compliance."""
    monitor_task_id = self.request.id
    logger.info(f"[{monitor_task_id}] Monitoring SLA for task: {monitored_task_id}")
    
    # Get task execution record
    execution = _task_executions.get(monitored_task_id)
    if not execution:
        logger.warning(f"[{monitor_task_id}] No execution record found for task: {monitored_task_id}")
        return {"status": "no_record", "task_id": monitored_task_id}
    
    # Check current status
    current_time = datetime.utcnow()
    total_time = (current_time - execution.submitted_at).total_seconds()
    
    sla_status = {
        "task_id": monitored_task_id,
        "monitor_task_id": monitor_task_id,
        "sla_target_seconds": sla_seconds,
        "elapsed_seconds": total_time,
        "sla_remaining_seconds": max(0, sla_seconds - total_time),
        "current_status": execution.status,
        "checked_at": current_time.isoformat()
    }
    
    if total_time > sla_seconds:
        # SLA violation
        sla_status["sla_violation"] = True
        sla_status["sla_exceeded_by_seconds"] = total_time - sla_seconds
        
        logger.warning(f"[{monitor_task_id}] SLA VIOLATION: Task {monitored_task_id} exceeded SLA by {total_time - sla_seconds:.1f}s")
        
        # Trigger SLA violation handlers
        handle_sla_violation.delay(monitored_task_id, sla_status)
        
    else:
        sla_status["sla_violation"] = False
        logger.info(f"[{monitor_task_id}] SLA OK: Task {monitored_task_id} within SLA")
    
    return sla_status


@celery_app.task(bind=True, name="priority.handle_sla_violation")
def handle_sla_violation(self, violated_task_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Handle SLA violations with escalation and notifications."""
    handler_task_id = self.request.id
    logger.warning(f"[{handler_task_id}] Handling SLA violation for task: {violated_task_id}")
    
    execution = _task_executions.get(violated_task_id)
    violation_severity = calculate_violation_severity(sla_status)
    
    # Determine violation response
    response_actions = []
    
    if violation_severity >= 0.5:  # 50% or more over SLA
        response_actions.extend([
            "send_critical_alert",
            "escalate_to_ops",
            "consider_task_cancellation"
        ])
    elif violation_severity >= 0.2:  # 20% or more over SLA
        response_actions.extend([
            "send_warning_alert",
            "increase_monitoring"
        ])
    else:
        response_actions.append("log_minor_violation")
    
    # Execute response actions
    for action in response_actions:
        execute_sla_response_action.delay(action, violated_task_id, sla_status)
    
    violation_response = {
        "violated_task_id": violated_task_id,
        "handler_task_id": handler_task_id,
        "violation_severity": violation_severity,
        "response_actions": response_actions,
        "handled_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"[{handler_task_id}] SLA violation handled with {len(response_actions)} actions")
    return violation_response


def calculate_violation_severity(sla_status: Dict[str, Any]) -> float:
    """Calculate severity of SLA violation as percentage over target."""
    exceeded_by = sla_status.get("sla_exceeded_by_seconds", 0)
    target = sla_status.get("sla_target_seconds", 1)
    return exceeded_by / target


@celery_app.task(bind=True, name="priority.execute_sla_response_action")
def execute_sla_response_action(self, action: str, task_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Execute specific SLA violation response actions."""
    action_task_id = self.request.id
    logger.info(f"[{action_task_id}] Executing SLA response action: {action}")
    
    # Simulate action execution
    time.sleep(random.uniform(0.1, 0.5))
    
    action_results = {
        "send_critical_alert": lambda: send_critical_sla_alert(task_id, sla_status),
        "send_warning_alert": lambda: send_warning_sla_alert(task_id, sla_status),
        "escalate_to_ops": lambda: escalate_to_operations(task_id, sla_status),
        "consider_task_cancellation": lambda: evaluate_task_cancellation(task_id, sla_status),
        "increase_monitoring": lambda: increase_task_monitoring(task_id, sla_status),
        "log_minor_violation": lambda: log_minor_violation(task_id, sla_status)
    }
    
    if action in action_results:
        result = action_results[action]()
    else:
        result = {"action": action, "status": "unknown_action"}
    
    result.update({
        "action_task_id": action_task_id,
        "executed_at": datetime.utcnow().isoformat()
    })
    
    return result


def send_critical_sla_alert(task_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Send critical alert for severe SLA violations."""
    return {
        "action": "send_critical_alert",
        "alert_level": "critical",
        "recipients": ["ops-team@example.com", "on-call@example.com"],
        "message": f"CRITICAL: Task {task_id} exceeded SLA by {sla_status.get('sla_exceeded_by_seconds', 0):.1f}s",
        "channels": ["email", "slack", "pagerduty"]
    }


def send_warning_sla_alert(task_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Send warning alert for moderate SLA violations."""
    return {
        "action": "send_warning_alert",
        "alert_level": "warning",
        "recipients": ["ops-team@example.com"],
        "message": f"WARNING: Task {task_id} exceeded SLA by {sla_status.get('sla_exceeded_by_seconds', 0):.1f}s",
        "channels": ["email", "slack"]
    }


def escalate_to_operations(task_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Escalate severe violations to operations team."""
    return {
        "action": "escalate_to_ops",
        "escalation_level": "L2",
        "assigned_to": "ops-escalation-team",
        "ticket_id": f"SLA-{random.randint(10000, 99999)}",
        "priority": "high"
    }


def evaluate_task_cancellation(task_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate whether to cancel severely delayed task."""
    exceeded_ratio = calculate_violation_severity(sla_status)
    should_cancel = exceeded_ratio > 3.0  # Cancel if 3x over SLA
    
    return {
        "action": "evaluate_cancellation",
        "should_cancel": should_cancel,
        "exceeded_ratio": exceeded_ratio,
        "recommendation": "cancel" if should_cancel else "continue_monitoring"
    }


def increase_task_monitoring(task_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Increase monitoring frequency for at-risk task."""
    return {
        "action": "increase_monitoring",
        "monitoring_frequency": "every_30_seconds",
        "additional_metrics": ["memory_usage", "cpu_usage", "queue_depth"]
    }


def log_minor_violation(task_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Log minor SLA violation for trend analysis."""
    return {
        "action": "log_minor_violation",
        "log_level": "info",
        "trend_analysis": True,
        "violation_category": "minor"
    }


# =============================================================================
# PRIORITY-BASED TASK IMPLEMENTATIONS
# =============================================================================

@celery_app.task(bind=True, name="priority.high_priority_data_processing")
def high_priority_data_processing(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """High-priority data processing with SLA guarantees."""
    task_id = self.request.id
    start_time = datetime.utcnow()
    
    # Update execution record
    if task_id in _task_executions:
        _task_executions[task_id].started_at = start_time
        _task_executions[task_id].status = "running"
    
    logger.info(f"[{task_id}] Starting high-priority data processing")
    
    # Optimized processing for high priority
    processing_time = config.get("processing_time", 0.5)  # Faster for high priority
    time.sleep(random.uniform(processing_time * 0.8, processing_time * 1.0))
    
    # Process data with high-priority optimizations
    result = {
        "task_id": task_id,
        "priority": "high",
        "data_processed": len(str(data)),
        "processing_optimizations": ["fast_path", "priority_cpu", "cached_resources"],
        "sla_target": config.get("sla_seconds", 5.0),
        "started_at": start_time.isoformat(),
        "completed_at": datetime.utcnow().isoformat()
    }
    
    # Update execution record
    if task_id in _task_executions:
        _task_executions[task_id].completed_at = datetime.utcnow()
        _task_executions[task_id].status = "completed"
        _task_executions[task_id].actual_duration = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(f"[{task_id}] High-priority processing completed")
    return result


@celery_app.task(bind=True, name="priority.background_batch_processing")
def background_batch_processing(self, batch_data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """Background batch processing with normal priority."""
    task_id = self.request.id
    start_time = datetime.utcnow()
    
    # Update execution record
    if task_id in _task_executions:
        _task_executions[task_id].started_at = start_time
        _task_executions[task_id].status = "running"
    
    logger.info(f"[{task_id}] Starting background batch processing: {len(batch_data)} items")
    
    # Standard processing for normal priority
    processing_time = config.get("processing_time", 2.0)
    time.sleep(random.uniform(processing_time * 0.9, processing_time * 1.2))
    
    # Process batch with standard optimizations
    processed_items = []
    for item in batch_data:
        processed_item = item.copy()
        processed_item["processed_at"] = datetime.utcnow().isoformat()
        processed_item["processor_task_id"] = task_id
        processed_items.append(processed_item)
    
    result = {
        "task_id": task_id,
        "priority": "normal",
        "batch_size": len(batch_data),
        "processed_items": len(processed_items),
        "processing_optimizations": ["standard_path", "shared_resources"],
        "sla_target": config.get("sla_seconds", 30.0),
        "started_at": start_time.isoformat(),
        "completed_at": datetime.utcnow().isoformat()
    }
    
    # Update execution record
    if task_id in _task_executions:
        _task_executions[task_id].completed_at = datetime.utcnow()
        _task_executions[task_id].status = "completed"
        _task_executions[task_id].actual_duration = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(f"[{task_id}] Background batch processing completed")
    return result


@celery_app.task(bind=True, name="priority.bulk_low_priority_processing")
def bulk_low_priority_processing(self, bulk_data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """Bulk processing with low priority and best-effort SLA."""
    task_id = self.request.id
    start_time = datetime.utcnow()
    
    # Update execution record
    if task_id in _task_executions:
        _task_executions[task_id].started_at = start_time
        _task_executions[task_id].status = "running"
    
    logger.info(f"[{task_id}] Starting bulk low-priority processing: {len(bulk_data)} items")
    
    # Slower processing for low priority (resource-efficient)
    processing_time = config.get("processing_time", 5.0)
    time.sleep(random.uniform(processing_time * 1.0, processing_time * 1.5))
    
    # Process bulk data with minimal resource usage
    processed_count = 0
    for i, item in enumerate(bulk_data):
        # Simulate processing with yield points for higher priority tasks
        if i % 10 == 0:
            time.sleep(0.1)  # Yield CPU periodically
        processed_count += 1
    
    result = {
        "task_id": task_id,
        "priority": "low",
        "bulk_size": len(bulk_data),
        "processed_items": processed_count,
        "processing_optimizations": ["resource_efficient", "yield_friendly"],
        "sla_target": None,  # Best effort
        "started_at": start_time.isoformat(),
        "completed_at": datetime.utcnow().isoformat()
    }
    
    # Update execution record
    if task_id in _task_executions:
        _task_executions[task_id].completed_at = datetime.utcnow()
        _task_executions[task_id].status = "completed"
        _task_executions[task_id].actual_duration = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(f"[{task_id}] Bulk low-priority processing completed")
    return result


# =============================================================================
# PRIORITY ANALYTICS AND REPORTING
# =============================================================================

@celery_app.task(bind=True, name="priority.analyze_priority_performance")
def analyze_priority_performance(self, time_range_hours: int = 24) -> Dict[str, Any]:
    """Analyze priority-based task performance and SLA compliance."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Analyzing priority performance for last {time_range_hours} hours")
    
    # Filter executions by time range
    cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
    recent_executions = [
        exec for exec in _task_executions.values()
        if exec.submitted_at >= cutoff_time
    ]
    
    # Group by priority levels
    priority_groups = {}
    for exec in recent_executions:
        priority_level = get_priority_level(exec.priority)
        if priority_level not in priority_groups:
            priority_groups[priority_level] = []
        priority_groups[priority_level].append(exec)
    
    # Calculate metrics for each priority level
    priority_analysis = {}
    for priority_level, executions in priority_groups.items():
        completed_executions = [e for e in executions if e.completed_at]
        
        if completed_executions:
            waiting_times = [e.waiting_time for e in completed_executions if e.waiting_time]
            total_times = [e.total_time for e in completed_executions if e.total_time]
            sla_met_count = sum(1 for e in completed_executions if e.sla_met is True)
            sla_total_count = sum(1 for e in completed_executions if e.sla_met is not None)
            
            priority_analysis[priority_level] = {
                "total_tasks": len(executions),
                "completed_tasks": len(completed_executions),
                "completion_rate": len(completed_executions) / len(executions) if executions else 0,
                "avg_waiting_time_seconds": sum(waiting_times) / len(waiting_times) if waiting_times else 0,
                "avg_total_time_seconds": sum(total_times) / len(total_times) if total_times else 0,
                "sla_compliance_rate": sla_met_count / sla_total_count if sla_total_count else None,
                "sla_violations": sla_total_count - sla_met_count if sla_total_count else 0
            }
    
    # Overall analysis
    all_completed = [e for e in recent_executions if e.completed_at]
    overall_sla_met = sum(1 for e in all_completed if e.sla_met is True)
    overall_sla_total = sum(1 for e in all_completed if e.sla_met is not None)
    
    analysis_result = {
        "analysis_period": {
            "start_time": cutoff_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_hours": time_range_hours
        },
        "overall_metrics": {
            "total_tasks": len(recent_executions),
            "completed_tasks": len(all_completed),
            "overall_completion_rate": len(all_completed) / len(recent_executions) if recent_executions else 0,
            "overall_sla_compliance": overall_sla_met / overall_sla_total if overall_sla_total else None,
            "total_sla_violations": overall_sla_total - overall_sla_met if overall_sla_total else 0
        },
        "priority_level_analysis": priority_analysis,
        "recommendations": generate_priority_recommendations(priority_analysis),
        "analyzed_at": datetime.utcnow().isoformat(),
        "analyzer_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Priority performance analysis complete")
    return analysis_result


def get_priority_level(priority_value: int) -> str:
    """Convert numeric priority to level name."""
    if priority_value >= Priority.CRITICAL.value:
        return "critical"
    elif priority_value >= Priority.HIGH.value:
        return "high"
    elif priority_value >= Priority.NORMAL.value:
        return "normal"
    elif priority_value >= Priority.LOW.value:
        return "low"
    else:
        return "bulk"


def generate_priority_recommendations(priority_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate recommendations based on priority performance analysis."""
    recommendations = []
    
    for priority_level, metrics in priority_analysis.items():
        sla_compliance = metrics.get("sla_compliance_rate", 1.0)
        completion_rate = metrics.get("completion_rate", 1.0)
        avg_waiting_time = metrics.get("avg_waiting_time_seconds", 0)
        
        if sla_compliance and sla_compliance < 0.95:  # Less than 95% SLA compliance
            recommendations.append({
                "priority_level": priority_level,
                "type": "sla_improvement",
                "message": f"SLA compliance for {priority_level} priority is {sla_compliance:.1%}. Consider increasing resources or adjusting SLA targets.",
                "urgency": "high" if priority_level in ["critical", "high"] else "medium"
            })
        
        if completion_rate < 0.9:  # Less than 90% completion rate
            recommendations.append({
                "priority_level": priority_level,
                "type": "completion_improvement",
                "message": f"Completion rate for {priority_level} priority is {completion_rate:.1%}. Investigate task failures.",
                "urgency": "high"
            })
        
        if avg_waiting_time > 60 and priority_level in ["critical", "high"]:  # High priority tasks waiting > 1 minute
            recommendations.append({
                "priority_level": priority_level,
                "type": "queue_optimization",
                "message": f"High-priority tasks waiting average {avg_waiting_time:.1f}s. Consider dedicated workers or queue optimization.",
                "urgency": "medium"
            })
    
    return recommendations


@celery_app.task(bind=True, name="priority.get_priority_queue_status")
def get_priority_queue_status(self) -> Dict[str, Any]:
    """Get current status of all priority queues."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Getting priority queue status")
    
    # Simulate queue status (in production, query actual queue depths)
    queue_status = {
        "critical_priority": {
            "depth": random.randint(0, 5),
            "workers": 5,
            "avg_processing_time": random.uniform(0.5, 2.0)
        },
        "high_priority": {
            "depth": random.randint(0, 20),
            "workers": 10,
            "avg_processing_time": random.uniform(1.0, 5.0)
        },
        "real_time": {
            "depth": random.randint(0, 10),
            "workers": 8,
            "avg_processing_time": random.uniform(0.1, 1.0)
        },
        "interactive": {
            "depth": random.randint(5, 50),
            "workers": 15,
            "avg_processing_time": random.uniform(2.0, 8.0)
        },
        "background": {
            "depth": random.randint(20, 200),
            "workers": 20,
            "avg_processing_time": random.uniform(5.0, 30.0)
        },
        "batch_processing": {
            "depth": random.randint(10, 100),
            "workers": 12,
            "avg_processing_time": random.uniform(30.0, 300.0)
        },
        "bulk_processing": {
            "depth": random.randint(50, 1000),
            "workers": 8,
            "avg_processing_time": random.uniform(60.0, 1800.0)
        }
    }
    
    # Calculate overall statistics
    total_depth = sum(q["depth"] for q in queue_status.values())
    total_workers = sum(q["workers"] for q in queue_status.values())
    
    status_summary = {
        "queue_details": queue_status,
        "overall_stats": {
            "total_queued_tasks": total_depth,
            "total_workers": total_workers,
            "worker_utilization": random.uniform(0.6, 0.9),
            "avg_queue_depth": total_depth / len(queue_status)
        },
        "alerts": generate_queue_alerts(queue_status),
        "checked_at": datetime.utcnow().isoformat(),
        "checker_task_id": task_id
    }
    
    return status_summary


def generate_queue_alerts(queue_status: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate alerts based on queue status."""
    alerts = []
    
    for queue_name, status in queue_status.items():
        depth = status["depth"]
        workers = status["workers"]
        
        # Alert thresholds based on queue type
        if "critical" in queue_name and depth > 2:
            alerts.append({
                "queue": queue_name,
                "type": "high_depth",
                "message": f"Critical queue depth ({depth}) exceeds safe threshold",
                "severity": "critical"
            })
        elif "high" in queue_name and depth > 10:
            alerts.append({
                "queue": queue_name,
                "type": "high_depth",
                "message": f"High priority queue depth ({depth}) is elevated",
                "severity": "warning"
            })
        elif depth > workers * 10:  # Queue depth > 10x workers
            alerts.append({
                "queue": queue_name,
                "type": "high_depth",
                "message": f"Queue depth ({depth}) significantly exceeds worker capacity ({workers})",
                "severity": "warning"
            })
    
    return alerts
