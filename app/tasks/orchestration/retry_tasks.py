"""
Advanced retry strategies and error handling patterns.

This module provides sophisticated retry mechanisms including exponential backoff,
circuit breakers, dead letter queues, and custom retry strategies for enterprise workflows.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta
import json
import random
import time
import math
from dataclasses import dataclass, field
from enum import Enum

from celery import signature
from celery.exceptions import Retry, Ignore, WorkerLostError
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Available retry strategies."""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"
    CUSTOM = "custom"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1  # 10% jitter
    retry_on_exceptions: List[str] = field(default_factory=lambda: ["Exception"])
    stop_on_exceptions: List[str] = field(default_factory=lambda: ["KeyboardInterrupt", "SystemExit"])
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0  # seconds
    dead_letter_queue: bool = True
    
    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for the given retry attempt."""
        if self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.base_delay
            
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = min(self.base_delay * (self.backoff_multiplier ** retry_count), self.max_delay)
            
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = min(self.base_delay * (retry_count + 1), self.max_delay)
            
        elif self.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            # Calculate fibonacci number for retry_count
            def fibonacci(n):
                if n <= 1:
                    return n
                a, b = 0, 1
                for _ in range(2, n + 1):
                    a, b = b, a + b
                return b
            
            delay = min(self.base_delay * fibonacci(retry_count + 1), self.max_delay)
            
        else:  # CUSTOM or default
            delay = self.base_delay
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)


# =============================================================================
# CIRCUIT BREAKER PATTERN
# =============================================================================

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast, not executing
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    next_attempt_time: Optional[datetime] = None


# Global circuit breaker registry (in production, use Redis or database)
_circuit_breakers: Dict[str, CircuitBreakerStats] = {}


def get_circuit_breaker(service_name: str) -> CircuitBreakerStats:
    """Get or create circuit breaker for service."""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreakerStats()
    return _circuit_breakers[service_name]


def check_circuit_breaker(service_name: str, threshold: int, timeout: float) -> bool:
    """Check if circuit breaker allows execution."""
    breaker = get_circuit_breaker(service_name)
    now = datetime.utcnow()
    
    if breaker.state == CircuitBreakerState.CLOSED:
        return True
    
    elif breaker.state == CircuitBreakerState.OPEN:
        if breaker.next_attempt_time and now >= breaker.next_attempt_time:
            breaker.state = CircuitBreakerState.HALF_OPEN
            return True
        return False
    
    else:  # HALF_OPEN
        return True


def record_circuit_breaker_success(service_name: str):
    """Record successful execution."""
    breaker = get_circuit_breaker(service_name)
    breaker.success_count += 1
    breaker.last_success_time = datetime.utcnow()
    
    if breaker.state == CircuitBreakerState.HALF_OPEN:
        breaker.state = CircuitBreakerState.CLOSED
        breaker.failure_count = 0


def record_circuit_breaker_failure(service_name: str, threshold: int, timeout: float):
    """Record failed execution."""
    breaker = get_circuit_breaker(service_name)
    breaker.failure_count += 1
    breaker.last_failure_time = datetime.utcnow()
    
    if breaker.failure_count >= threshold:
        breaker.state = CircuitBreakerState.OPEN
        breaker.next_attempt_time = datetime.utcnow() + timedelta(seconds=timeout)


# =============================================================================
# RETRY DECORATORS AND UTILITIES
# =============================================================================

def smart_retry(retry_config: RetryConfig):
    """Decorator for adding smart retry logic to Celery tasks."""
    def decorator(task_func):
        def wrapper(self, *args, **kwargs):
            task_id = self.request.id
            retry_count = self.request.retries
            
            # Check circuit breaker if configured
            service_name = kwargs.get("service_name", task_func.__name__)
            if retry_config.circuit_breaker_threshold > 0:
                if not check_circuit_breaker(
                    service_name, 
                    retry_config.circuit_breaker_threshold, 
                    retry_config.circuit_breaker_timeout
                ):
                    logger.warning(f"[{task_id}] Circuit breaker OPEN for {service_name}")
                    raise Ignore(f"Circuit breaker open for {service_name}")
            
            try:
                logger.info(f"[{task_id}] Executing {task_func.__name__} (attempt {retry_count + 1})")
                result = task_func(self, *args, **kwargs)
                
                # Record success for circuit breaker
                if retry_config.circuit_breaker_threshold > 0:
                    record_circuit_breaker_success(service_name)
                
                return result
                
            except Exception as exc:
                # Log the exception
                logger.error(f"[{task_id}] {task_func.__name__} failed (attempt {retry_count + 1}): {exc}")
                
                # Check if we should stop on this exception
                exc_name = exc.__class__.__name__
                if exc_name in retry_config.stop_on_exceptions:
                    logger.error(f"[{task_id}] Stopping retries due to {exc_name}")
                    raise exc
                
                # Check if we should retry on this exception
                should_retry = any(
                    exc_name == retry_exc or issubclass(exc.__class__, globals().get(retry_exc, Exception))
                    for retry_exc in retry_config.retry_on_exceptions
                )
                
                if not should_retry:
                    logger.error(f"[{task_id}] Not retrying for exception {exc_name}")
                    raise exc
                
                # Check retry limits
                if retry_count >= retry_config.max_retries:
                    logger.error(f"[{task_id}] Max retries ({retry_config.max_retries}) exceeded")
                    
                    # Send to dead letter queue if configured
                    if retry_config.dead_letter_queue:
                        send_to_dead_letter_queue.delay(
                            task_name=task_func.__name__,
                            task_args=args,
                            task_kwargs=kwargs,
                            final_exception=str(exc),
                            retry_count=retry_count,
                            task_id=task_id
                        )
                    
                    raise exc
                
                # Record failure for circuit breaker
                if retry_config.circuit_breaker_threshold > 0:
                    record_circuit_breaker_failure(
                        service_name,
                        retry_config.circuit_breaker_threshold,
                        retry_config.circuit_breaker_timeout
                    )
                
                # Calculate retry delay
                delay = retry_config.calculate_delay(retry_count)
                
                logger.info(f"[{task_id}] Retrying in {delay:.1f} seconds (attempt {retry_count + 2}/{retry_config.max_retries + 1})")
                
                # Raise Retry exception to trigger Celery's retry mechanism
                raise self.retry(exc=exc, countdown=delay)
                
        return wrapper
    return decorator


# =============================================================================
# RETRY-ENABLED TASKS
# =============================================================================

@celery_app.task(bind=True, name="retry.unreliable_service_call")
@smart_retry(RetryConfig(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,
    max_delay=60.0,
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=30.0
))
def unreliable_service_call(self, service_url: str, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Simulate calling an unreliable external service."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Calling unreliable service: {service_url}")
    
    # Simulate network delay
    time.sleep(random.uniform(0.1, 0.5))
    
    # Simulate various failure scenarios
    failure_scenario = random.choice([
        "success", "success", "success",  # 60% success rate
        "timeout", "connection_error", "server_error", "rate_limit"
    ])
    
    if failure_scenario == "timeout":
        raise TimeoutError(f"Service {service_url} timed out")
    elif failure_scenario == "connection_error":
        raise ConnectionError(f"Failed to connect to {service_url}")
    elif failure_scenario == "server_error":
        raise Exception(f"Server error from {service_url}: Internal server error")
    elif failure_scenario == "rate_limit":
        raise Exception(f"Rate limit exceeded for {service_url}")
    
    # Success case
    response = {
        "service_url": service_url,
        "request_data": request_data,
        "response_data": {"result": "success", "timestamp": datetime.utcnow().isoformat()},
        "task_id": task_id,
        "attempt_number": self.request.retries + 1
    }
    
    logger.info(f"[{task_id}] Service call successful")
    return response


@celery_app.task(bind=True, name="retry.database_operation")
@smart_retry(RetryConfig(
    max_retries=3,
    strategy=RetryStrategy.LINEAR_BACKOFF,
    base_delay=2.0,
    retry_on_exceptions=["ConnectionError", "TimeoutError", "OperationalError"],
    stop_on_exceptions=["ValueError", "TypeError"]
))
def database_operation(self, operation: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Simulate database operations with retry logic."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Performing database operation: {operation}")
    
    # Simulate database processing time
    time.sleep(random.uniform(0.2, 1.0))
    
    # Simulate database issues
    failure_scenario = random.choice([
        "success", "success", "success", "success",  # 80% success rate
        "connection_lost", "deadlock", "timeout"
    ])
    
    if failure_scenario == "connection_lost":
        raise ConnectionError("Database connection lost")
    elif failure_scenario == "deadlock":
        raise Exception("Database deadlock detected")  # OperationalError in real scenarios
    elif failure_scenario == "timeout":
        raise TimeoutError("Database operation timed out")
    
    # Success case
    result = {
        "operation": operation,
        "data": data,
        "result": {"status": "success", "affected_rows": random.randint(1, 10)},
        "executed_at": datetime.utcnow().isoformat(),
        "task_id": task_id,
        "attempt_number": self.request.retries + 1
    }
    
    logger.info(f"[{task_id}] Database operation successful")
    return result


@celery_app.task(bind=True, name="retry.file_processing")
@smart_retry(RetryConfig(
    max_retries=4,
    strategy=RetryStrategy.FIBONACCI_BACKOFF,
    base_delay=1.0,
    max_delay=120.0,
    jitter=True
))
def file_processing(self, file_path: str, processing_options: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Simulate file processing with sophisticated retry logic."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Processing file: {file_path}")
    
    # Simulate file processing time
    processing_time = processing_options.get("processing_time", 1.0)
    time.sleep(random.uniform(processing_time * 0.5, processing_time * 1.5))
    
    # Simulate file processing issues
    failure_scenario = random.choice([
        "success", "success", "success",  # 75% success rate
        "file_locked", "disk_full", "permission_denied"
    ])
    
    if failure_scenario == "file_locked":
        raise Exception(f"File {file_path} is locked by another process")
    elif failure_scenario == "disk_full":
        raise Exception("Insufficient disk space for processing")
    elif failure_scenario == "permission_denied":
        raise PermissionError(f"Permission denied accessing {file_path}")
    
    # Success case
    result = {
        "file_path": file_path,
        "processing_options": processing_options,
        "result": {
            "status": "processed",
            "file_size": random.randint(1024, 1024*1024),
            "checksum": f"sha256:{random.randint(1000000, 9999999)}"
        },
        "processed_at": datetime.utcnow().isoformat(),
        "task_id": task_id,
        "attempt_number": self.request.retries + 1
    }
    
    logger.info(f"[{task_id}] File processing successful")
    return result


# =============================================================================
# DEAD LETTER QUEUE AND ERROR RECOVERY
# =============================================================================

@celery_app.task(bind=True, name="retry.send_to_dead_letter_queue")
def send_to_dead_letter_queue(self, task_name: str, task_args: tuple, task_kwargs: dict, 
                             final_exception: str, retry_count: int, task_id: str) -> Dict[str, Any]:
    """Send failed task to dead letter queue for manual review."""
    dlq_task_id = self.request.id
    logger.warning(f"[{dlq_task_id}] Sending task {task_name} to dead letter queue after {retry_count} retries")
    
    dead_letter_record = {
        "dlq_id": f"dlq_{dlq_task_id}",
        "original_task_id": task_id,
        "task_name": task_name,
        "task_args": task_args,
        "task_kwargs": task_kwargs,
        "final_exception": final_exception,
        "retry_count": retry_count,
        "failed_at": datetime.utcnow().isoformat(),
        "status": "pending_review"
    }
    
    # In production, save to persistent storage (database, message queue, etc.)
    logger.info(f"[{dlq_task_id}] Dead letter record created: {dead_letter_record['dlq_id']}")
    
    return dead_letter_record


@celery_app.task(bind=True, name="retry.recover_from_dead_letter_queue")
def recover_from_dead_letter_queue(self, dlq_id: str, recovery_strategy: str = "retry") -> Dict[str, Any]:
    """Recover tasks from dead letter queue."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Recovering from dead letter queue: {dlq_id}, strategy: {recovery_strategy}")
    
    # In production, retrieve from persistent storage
    # For demonstration, simulate recovery
    
    recovery_result = {
        "dlq_id": dlq_id,
        "recovery_strategy": recovery_strategy,
        "recovered_at": datetime.utcnow().isoformat(),
        "recovery_task_id": task_id
    }
    
    if recovery_strategy == "retry":
        # Re-queue the original task with modified parameters
        recovery_result["action"] = "task_requeued"
        recovery_result["new_task_id"] = f"recovered_{random.randint(1000, 9999)}"
        
    elif recovery_strategy == "manual_fix":
        # Mark for manual intervention
        recovery_result["action"] = "marked_for_manual_fix"
        recovery_result["assigned_to"] = "support_team"
        
    elif recovery_strategy == "discard":
        # Permanently discard the task
        recovery_result["action"] = "discarded"
        recovery_result["reason"] = "irrecoverable_error"
    
    logger.info(f"[{task_id}] Recovery complete: {recovery_result['action']}")
    return recovery_result


# =============================================================================
# RETRY ANALYTICS AND MONITORING
# =============================================================================

@celery_app.task(bind=True, name="retry.analyze_retry_patterns")
def analyze_retry_patterns(self, time_range_hours: int = 24) -> Dict[str, Any]:
    """Analyze retry patterns and failure modes."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Analyzing retry patterns for last {time_range_hours} hours")
    
    # In production, query actual task execution data
    # For demonstration, simulate analysis
    
    analysis_start = datetime.utcnow() - timedelta(hours=time_range_hours)
    
    retry_analysis = {
        "analysis_period": {
            "start_time": analysis_start.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_hours": time_range_hours
        },
        "overall_stats": {
            "total_tasks_executed": random.randint(1000, 10000),
            "tasks_with_retries": random.randint(100, 1000),
            "retry_rate_percent": random.uniform(5, 25),
            "average_retries_per_task": random.uniform(1.5, 3.0),
            "max_retries_observed": random.randint(3, 10)
        },
        "failure_patterns": {
            "timeout_errors": random.randint(20, 200),
            "connection_errors": random.randint(15, 150),
            "rate_limit_errors": random.randint(5, 50),
            "server_errors": random.randint(10, 100),
            "unknown_errors": random.randint(2, 20)
        },
        "retry_strategies": {
            "exponential_backoff": random.randint(400, 4000),
            "linear_backoff": random.randint(200, 2000),
            "fixed_delay": random.randint(100, 1000),
            "fibonacci_backoff": random.randint(50, 500)
        },
        "circuit_breaker_stats": {
            "services_monitored": len(_circuit_breakers),
            "circuit_breakers_triggered": sum(1 for cb in _circuit_breakers.values() if cb.state != CircuitBreakerState.CLOSED),
            "current_open_circuits": [name for name, cb in _circuit_breakers.items() if cb.state == CircuitBreakerState.OPEN]
        },
        "recommendations": generate_retry_recommendations()
    }
    
    logger.info(f"[{task_id}] Retry pattern analysis complete")
    return retry_analysis


def generate_retry_recommendations() -> List[Dict[str, str]]:
    """Generate recommendations based on retry patterns."""
    recommendations = []
    
    # Sample recommendations based on common patterns
    recommendations.extend([
        {
            "type": "strategy",
            "message": "Consider using exponential backoff for timeout-prone services",
            "priority": "medium"
        },
        {
            "type": "configuration",
            "message": "Increase circuit breaker timeout for external API calls",
            "priority": "high"
        },
        {
            "type": "monitoring",
            "message": "Set up alerts for retry rates exceeding 20%",
            "priority": "low"
        },
        {
            "type": "optimization",
            "message": "Implement request deduplication for idempotent operations",
            "priority": "medium"
        }
    ])
    
    return recommendations


@celery_app.task(bind=True, name="retry.reset_circuit_breaker")
def reset_circuit_breaker(self, service_name: str) -> Dict[str, Any]:
    """Manually reset a circuit breaker."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Resetting circuit breaker for service: {service_name}")
    
    if service_name in _circuit_breakers:
        old_state = _circuit_breakers[service_name].state
        _circuit_breakers[service_name] = CircuitBreakerStats()
        
        result = {
            "service_name": service_name,
            "old_state": old_state.value,
            "new_state": CircuitBreakerState.CLOSED.value,
            "reset_at": datetime.utcnow().isoformat(),
            "reset_by_task": task_id
        }
        
        logger.info(f"[{task_id}] Circuit breaker reset successful: {service_name}")
    else:
        result = {
            "service_name": service_name,
            "status": "not_found",
            "message": f"No circuit breaker found for service: {service_name}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.warning(f"[{task_id}] Circuit breaker not found: {service_name}")
    
    return result


@celery_app.task(bind=True, name="retry.get_circuit_breaker_status")
def get_circuit_breaker_status(self, service_name: Optional[str] = None) -> Dict[str, Any]:
    """Get current circuit breaker status."""
    task_id = self.request.id
    
    if service_name:
        logger.info(f"[{task_id}] Getting circuit breaker status for: {service_name}")
        
        if service_name in _circuit_breakers:
            breaker = _circuit_breakers[service_name]
            status = {
                "service_name": service_name,
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "success_count": breaker.success_count,
                "last_failure_time": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
                "last_success_time": breaker.last_success_time.isoformat() if breaker.last_success_time else None,
                "next_attempt_time": breaker.next_attempt_time.isoformat() if breaker.next_attempt_time else None
            }
        else:
            status = {
                "service_name": service_name,
                "status": "not_found",
                "message": f"No circuit breaker registered for service: {service_name}"
            }
    else:
        logger.info(f"[{task_id}] Getting all circuit breaker statuses")
        status = {
            "total_circuit_breakers": len(_circuit_breakers),
            "circuit_breakers": {
                name: {
                    "state": breaker.state.value,
                    "failure_count": breaker.failure_count,
                    "success_count": breaker.success_count
                }
                for name, breaker in _circuit_breakers.items()
            },
            "summary": {
                "closed": sum(1 for cb in _circuit_breakers.values() if cb.state == CircuitBreakerState.CLOSED),
                "open": sum(1 for cb in _circuit_breakers.values() if cb.state == CircuitBreakerState.OPEN),
                "half_open": sum(1 for cb in _circuit_breakers.values() if cb.state == CircuitBreakerState.HALF_OPEN)
            }
        }
    
    return status
