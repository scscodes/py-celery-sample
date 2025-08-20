"""
Advanced Celery Orchestration Module

This module provides enterprise-grade orchestration patterns for complex workflow management,
including workflow execution, batch processing, retry strategies, callbacks, priority management,
and comprehensive monitoring.

Available Orchestration Patterns:
===============================

1. Workflow Tasks (workflow_tasks.py):
   - Linear workflows with chained dependencies
   - Parallel workflows with concurrent execution
   - Chord workflows with aggregation callbacks
   - Map-reduce style processing
   - Complex multi-stage workflow orchestration

2. Batch Processing (batch_tasks.py):
   - Chunked batch processing with parallel execution
   - Progressive batch processing with adaptive error handling
   - Priority-based batch processing with SLA guarantees
   - Batch monitoring and progress tracking

3. Retry & Error Handling (retry_tasks.py):
   - Smart retry decorators with exponential backoff
   - Circuit breaker pattern implementation
   - Dead letter queue for failed tasks
   - Advanced retry strategies (fixed, exponential, fibonacci)
   - Retry pattern analysis and monitoring

4. Callback Management (callbacks_tasks.py):
   - Success/failure callback orchestration
   - Cleanup task scheduling
   - Notification and audit trail generation
   - Batch callback execution
   - Comprehensive lifecycle management

5. Priority Management (priority_tasks.py):
   - Priority-based task routing and execution
   - SLA monitoring and enforcement
   - Priority queue management
   - Performance analysis by priority level
   - Automatic SLA violation handling

6. System Monitoring (monitoring_tasks.py):
   - Comprehensive health checks (CPU, memory, disk, network)
   - System and Celery performance monitoring
   - Alert evaluation and notification
   - Monitoring report generation
   - Proactive alerting with multiple channels

Usage Examples:
==============

# Workflow Orchestration
from app.tasks.orchestration.workflow_tasks import linear_workflow, complex_workflow_orchestrator

# Submit a linear workflow
workflow_result = linear_workflow.delay(
    input_data={"user_id": 123, "data": "sample"},
    workflow_config={
        "validation_rules": {"required_fields": ["user_id"]},
        "transformation_config": {"uppercase_fields": ["status"]},
        "enrichment_config": {"user_lookup": True},
        "storage_config": {"backend": "database"}
    }
)

# Batch Processing
from app.tasks.orchestration.batch_tasks import chunked_batch_processor

# Process large batch with chunking
batch_result = chunked_batch_processor.delay(
    data_items=[{"id": i, "data": f"item_{i}"} for i in range(1000)],
    batch_config={
        "chunk_size": 50,
        "processing_config": {"type": "validation", "processing_time": 0.5}
    }
)

# Priority Task Submission
from app.tasks.orchestration.priority_tasks import submit_priority_task

# Submit high-priority task with SLA
priority_result = submit_priority_task.delay(
    task_name="priority.high_priority_data_processing",
    task_args=[{"urgent_data": "value"}],
    task_kwargs={"config": {"processing_time": 0.3}},
    config={
        "priority": 75,
        "queue_type": "interactive",
        "sla_seconds": 5.0,
        "timeout_seconds": 10.0
    }
)

# System Monitoring
from app.tasks.orchestration.monitoring_tasks import full_monitoring_cycle

# Run complete monitoring cycle
monitoring_result = full_monitoring_cycle.delay(
    monitoring_config={
        "alert_rules": [
            {
                "name": "high_cpu",
                "metric_path": "system.cpu.percent",
                "operator": "gt",
                "threshold": 80,
                "severity": "warning"
            }
        ]
    }
)

# Retry with Circuit Breaker
from app.tasks.orchestration.retry_tasks import unreliable_service_call

# Call service with smart retry and circuit breaker
service_result = unreliable_service_call.delay(
    service_url="https://api.external-service.com/data",
    request_data={"query": "sample"},
    service_name="external_api"
)

Available Tasks:
===============

Workflow Tasks:
- orchestration.validate_data
- orchestration.transform_data
- orchestration.enrichment_lookup
- orchestration.save_to_storage
- orchestration.send_notification
- orchestration.linear_workflow
- orchestration.parallel_workflow
- orchestration.chord_workflow
- orchestration.map_reduce_workflow
- orchestration.complex_workflow_orchestrator

Batch Processing Tasks:
- batch.process_single_item
- batch.process_chunk
- batch.aggregate_batch_results
- batch.chunked_batch_processor
- batch.progressive_batch_processor
- batch.priority_batch_processor
- batch.get_batch_status
- batch.cancel_batch

Retry & Error Handling Tasks:
- retry.unreliable_service_call
- retry.database_operation
- retry.file_processing
- retry.send_to_dead_letter_queue
- retry.recover_from_dead_letter_queue
- retry.analyze_retry_patterns
- retry.reset_circuit_breaker
- retry.get_circuit_breaker_status

Callback Management Tasks:
- callbacks.execute_callback
- callbacks.schedule_cleanup_callbacks
- callbacks.send_task_notification
- callbacks.audit_task_execution
- callbacks.batch_callback_executor
- callbacks.example_task_with_callbacks

Priority Management Tasks:
- priority.submit_priority_task
- priority.monitor_task_sla
- priority.handle_sla_violation
- priority.execute_sla_response_action
- priority.high_priority_data_processing
- priority.background_batch_processing
- priority.bulk_low_priority_processing
- priority.analyze_priority_performance
- priority.get_priority_queue_status

System Monitoring Tasks:
- monitoring.system_health_check
- monitoring.collect_system_metrics
- monitoring.collect_celery_metrics
- monitoring.evaluate_alerts
- monitoring.send_alert_notification
- monitoring.full_monitoring_cycle
- monitoring.generate_monitoring_report

Configuration Classes:
=====================

- RetryConfig: Configure retry behavior and circuit breakers
- CallbackConfig: Configure task lifecycle callbacks
- PriorityTaskConfig: Configure priority and SLA requirements
- HealthCheck: Represent health check results
- SystemMetrics: System performance data structures
"""

# Import all orchestration modules to register tasks
from . import workflow_tasks
from . import batch_tasks
from . import retry_tasks
from . import callbacks_tasks
from . import priority_tasks
from . import monitoring_tasks

# Export key classes for external use
from .retry_tasks import RetryConfig, RetryStrategy, CircuitBreakerState
from .callbacks_tasks import CallbackConfig, CallbackType
from .priority_tasks import PriorityTaskConfig, Priority, QueueType
from .monitoring_tasks import HealthStatus, HealthCheck, SystemMetrics

# Export commonly used decorators and utilities
from .retry_tasks import smart_retry
from .callbacks_tasks import with_callbacks

__all__ = [
    # Modules
    'workflow_tasks',
    'batch_tasks', 
    'retry_tasks',
    'callbacks_tasks',
    'priority_tasks',
    'monitoring_tasks',
    
    # Configuration Classes
    'RetryConfig',
    'RetryStrategy', 
    'CircuitBreakerState',
    'CallbackConfig',
    'CallbackType',
    'PriorityTaskConfig',
    'Priority',
    'QueueType',
    'HealthStatus',
    'HealthCheck',
    'SystemMetrics',
    
    # Decorators and Utilities
    'smart_retry',
    'with_callbacks'
]
