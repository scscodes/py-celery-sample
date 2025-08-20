"""
Health checks and system monitoring for Celery task infrastructure.

This module provides comprehensive monitoring capabilities including system health checks,
performance monitoring, resource utilization tracking, and proactive alerting.
"""

import logging
import psutil
import platform
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import json
import random
import time
from dataclasses import dataclass
from enum import Enum

from celery import signature
from celery.events.state import State
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning" 
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of metrics to collect."""
    SYSTEM = "system"
    CELERY = "celery"
    APPLICATION = "application"
    BUSINESS = "business"


@dataclass
class HealthCheck:
    """Health check result."""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    checked_at: datetime
    response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at.isoformat(),
            "response_time_ms": self.response_time_ms
        }


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    load_average: List[float]
    process_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "network_io": self.network_io,
            "load_average": self.load_average,
            "process_count": self.process_count
        }


# =============================================================================
# SYSTEM HEALTH CHECKS
# =============================================================================

@celery_app.task(bind=True, name="monitoring.system_health_check")
def system_health_check(self) -> Dict[str, Any]:
    """Comprehensive system health check."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting comprehensive system health check")
    
    health_checks = []
    start_time = datetime.utcnow()
    
    # CPU Health Check
    health_checks.append(check_cpu_health())
    
    # Memory Health Check
    health_checks.append(check_memory_health())
    
    # Disk Health Check
    health_checks.append(check_disk_health())
    
    # Network Health Check
    health_checks.append(check_network_health())
    
    # Celery Health Check
    health_checks.append(check_celery_health())
    
    # Database Health Check
    health_checks.append(check_database_health())
    
    # Redis Health Check
    health_checks.append(check_redis_health())
    
    # External Services Health Check
    health_checks.append(check_external_services_health())
    
    # Determine overall health status
    overall_status = determine_overall_health(health_checks)
    
    end_time = datetime.utcnow()
    total_time = (end_time - start_time).total_seconds() * 1000  # milliseconds
    
    health_report = {
        "overall_status": overall_status.value,
        "total_checks": len(health_checks),
        "healthy_checks": sum(1 for hc in health_checks if hc.status == HealthStatus.HEALTHY),
        "warning_checks": sum(1 for hc in health_checks if hc.status == HealthStatus.WARNING),
        "critical_checks": sum(1 for hc in health_checks if hc.status == HealthStatus.CRITICAL),
        "total_check_time_ms": total_time,
        "health_checks": [hc.to_dict() for hc in health_checks],
        "checked_at": end_time.isoformat(),
        "checker_task_id": task_id
    }
    
    logger.info(f"[{task_id}] System health check complete: {overall_status.value}")
    return health_report


def check_cpu_health() -> HealthCheck:
    """Check CPU utilization and health."""
    start_time = datetime.utcnow()
    
    try:
        # Get CPU usage over a brief interval
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        details = {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "load_average_1min": load_avg[0],
            "load_average_5min": load_avg[1],
            "load_average_15min": load_avg[2]
        }
        
        # Determine status
        if cpu_percent > 90:
            status = HealthStatus.CRITICAL
            message = f"CPU usage critically high: {cpu_percent:.1f}%"
        elif cpu_percent > 80:
            status = HealthStatus.WARNING
            message = f"CPU usage elevated: {cpu_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"CPU usage normal: {cpu_percent:.1f}%"
        
    except Exception as e:
        status = HealthStatus.UNKNOWN
        message = f"Failed to check CPU health: {e}"
        details = {"error": str(e)}
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    return HealthCheck("cpu", status, message, details, datetime.utcnow(), response_time)


def check_memory_health() -> HealthCheck:
    """Check memory utilization and health."""
    start_time = datetime.utcnow()
    
    try:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        details = {
            "memory_total_gb": memory.total / (1024**3),
            "memory_available_gb": memory.available / (1024**3),
            "memory_percent": memory.percent,
            "swap_total_gb": swap.total / (1024**3),
            "swap_used_gb": swap.used / (1024**3),
            "swap_percent": swap.percent
        }
        
        # Determine status
        if memory.percent > 95:
            status = HealthStatus.CRITICAL
            message = f"Memory usage critically high: {memory.percent:.1f}%"
        elif memory.percent > 85:
            status = HealthStatus.WARNING
            message = f"Memory usage elevated: {memory.percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Memory usage normal: {memory.percent:.1f}%"
        
    except Exception as e:
        status = HealthStatus.UNKNOWN
        message = f"Failed to check memory health: {e}"
        details = {"error": str(e)}
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    return HealthCheck("memory", status, message, details, datetime.utcnow(), response_time)


def check_disk_health() -> HealthCheck:
    """Check disk utilization and health."""
    start_time = datetime.utcnow()
    
    try:
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        details = {
            "disk_total_gb": disk_usage.total / (1024**3),
            "disk_used_gb": disk_usage.used / (1024**3),
            "disk_free_gb": disk_usage.free / (1024**3),
            "disk_percent": disk_percent,
            "read_bytes": disk_io.read_bytes if disk_io else 0,
            "write_bytes": disk_io.write_bytes if disk_io else 0,
            "read_count": disk_io.read_count if disk_io else 0,
            "write_count": disk_io.write_count if disk_io else 0
        }
        
        # Determine status
        if disk_percent > 95:
            status = HealthStatus.CRITICAL
            message = f"Disk usage critically high: {disk_percent:.1f}%"
        elif disk_percent > 85:
            status = HealthStatus.WARNING
            message = f"Disk usage elevated: {disk_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Disk usage normal: {disk_percent:.1f}%"
        
    except Exception as e:
        status = HealthStatus.UNKNOWN
        message = f"Failed to check disk health: {e}"
        details = {"error": str(e)}
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    return HealthCheck("disk", status, message, details, datetime.utcnow(), response_time)


def check_network_health() -> HealthCheck:
    """Check network connectivity and health."""
    start_time = datetime.utcnow()
    
    try:
        network_io = psutil.net_io_counters()
        network_connections = len(psutil.net_connections())
        
        details = {
            "bytes_sent": network_io.bytes_sent,
            "bytes_recv": network_io.bytes_recv,
            "packets_sent": network_io.packets_sent,
            "packets_recv": network_io.packets_recv,
            "errors_in": network_io.errin,
            "errors_out": network_io.errout,
            "active_connections": network_connections
        }
        
        # Check for network errors
        total_errors = network_io.errin + network_io.errout
        if total_errors > 1000:
            status = HealthStatus.WARNING
            message = f"Network errors detected: {total_errors}"
        else:
            status = HealthStatus.HEALTHY
            message = "Network health normal"
        
    except Exception as e:
        status = HealthStatus.UNKNOWN
        message = f"Failed to check network health: {e}"
        details = {"error": str(e)}
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    return HealthCheck("network", status, message, details, datetime.utcnow(), response_time)


def check_celery_health() -> HealthCheck:
    """Check Celery worker and queue health."""
    start_time = datetime.utcnow()
    
    try:
        # Simulate Celery health check (in production, use actual Celery inspect)
        # inspect = celery_app.control.inspect()
        # active_workers = inspect.active() or {}
        # registered_tasks = inspect.registered() or {}
        
        # Simulated health data
        active_workers = {f"worker{i}@hostname": [] for i in range(1, random.randint(3, 8))}
        queue_lengths = {
            "celery": random.randint(0, 50),
            "priority": random.randint(0, 20),
            "batch": random.randint(0, 100)
        }
        
        total_workers = len(active_workers)
        total_queued = sum(queue_lengths.values())
        
        details = {
            "active_workers": total_workers,
            "queue_lengths": queue_lengths,
            "total_queued_tasks": total_queued,
            "worker_names": list(active_workers.keys())
        }
        
        # Determine status
        if total_workers == 0:
            status = HealthStatus.CRITICAL
            message = "No active Celery workers"
        elif total_queued > 1000:
            status = HealthStatus.WARNING
            message = f"High queue backlog: {total_queued} tasks"
        else:
            status = HealthStatus.HEALTHY
            message = f"Celery healthy: {total_workers} workers, {total_queued} queued"
        
    except Exception as e:
        status = HealthStatus.UNKNOWN
        message = f"Failed to check Celery health: {e}"
        details = {"error": str(e)}
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    return HealthCheck("celery", status, message, details, datetime.utcnow(), response_time)


def check_database_health() -> HealthCheck:
    """Check database connectivity and health."""
    start_time = datetime.utcnow()
    
    try:
        # Simulate database health check
        time.sleep(random.uniform(0.05, 0.2))  # Simulate DB query time
        
        # Simulated database metrics
        connection_pool_size = random.randint(10, 50)
        active_connections = random.randint(5, connection_pool_size - 5)
        avg_query_time = random.uniform(10, 100)  # milliseconds
        
        details = {
            "connection_pool_size": connection_pool_size,
            "active_connections": active_connections,
            "pool_utilization": (active_connections / connection_pool_size) * 100,
            "avg_query_time_ms": avg_query_time,
            "database_size_gb": random.uniform(10, 1000)
        }
        
        # Determine status
        pool_utilization = (active_connections / connection_pool_size) * 100
        if pool_utilization > 90:
            status = HealthStatus.WARNING
            message = f"Database connection pool highly utilized: {pool_utilization:.1f}%"
        elif avg_query_time > 1000:
            status = HealthStatus.WARNING
            message = f"Slow database queries detected: {avg_query_time:.1f}ms avg"
        else:
            status = HealthStatus.HEALTHY
            message = "Database health normal"
        
    except Exception as e:
        status = HealthStatus.CRITICAL
        message = f"Database connection failed: {e}"
        details = {"error": str(e)}
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    return HealthCheck("database", status, message, details, datetime.utcnow(), response_time)


def check_redis_health() -> HealthCheck:
    """Check Redis connectivity and health."""
    start_time = datetime.utcnow()
    
    try:
        # Simulate Redis health check
        time.sleep(random.uniform(0.01, 0.05))  # Simulate Redis ping time
        
        # Simulated Redis metrics
        memory_usage = random.uniform(100, 2000)  # MB
        connected_clients = random.randint(10, 200)
        ops_per_sec = random.randint(1000, 10000)
        
        details = {
            "memory_usage_mb": memory_usage,
            "connected_clients": connected_clients,
            "ops_per_second": ops_per_sec,
            "hit_rate_percent": random.uniform(85, 99),
            "keyspace_hits": random.randint(10000, 1000000),
            "keyspace_misses": random.randint(1000, 100000)
        }
        
        # Determine status
        if memory_usage > 1500:
            status = HealthStatus.WARNING
            message = f"Redis memory usage high: {memory_usage:.1f}MB"
        elif connected_clients > 150:
            status = HealthStatus.WARNING
            message = f"High Redis client connections: {connected_clients}"
        else:
            status = HealthStatus.HEALTHY
            message = "Redis health normal"
        
    except Exception as e:
        status = HealthStatus.CRITICAL
        message = f"Redis connection failed: {e}"
        details = {"error": str(e)}
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    return HealthCheck("redis", status, message, details, datetime.utcnow(), response_time)


def check_external_services_health() -> HealthCheck:
    """Check external service dependencies."""
    start_time = datetime.utcnow()
    
    try:
        # Simulate external service checks
        services = ["payment_api", "notification_service", "analytics_api", "third_party_integration"]
        service_statuses = {}
        
        for service in services:
            # Simulate service check
            time.sleep(random.uniform(0.1, 0.3))
            is_healthy = random.choice([True, True, True, False])  # 75% healthy
            response_time = random.uniform(100, 2000)
            
            service_statuses[service] = {
                "healthy": is_healthy,
                "response_time_ms": response_time,
                "last_checked": datetime.utcnow().isoformat()
            }
        
        healthy_services = sum(1 for s in service_statuses.values() if s["healthy"])
        total_services = len(services)
        
        details = {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "service_statuses": service_statuses
        }
        
        # Determine status
        if healthy_services == 0:
            status = HealthStatus.CRITICAL
            message = "All external services are down"
        elif healthy_services < total_services * 0.5:
            status = HealthStatus.CRITICAL
            message = f"Majority of external services down: {healthy_services}/{total_services}"
        elif healthy_services < total_services:
            status = HealthStatus.WARNING
            message = f"Some external services down: {healthy_services}/{total_services}"
        else:
            status = HealthStatus.HEALTHY
            message = "All external services healthy"
        
    except Exception as e:
        status = HealthStatus.UNKNOWN
        message = f"Failed to check external services: {e}"
        details = {"error": str(e)}
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    return HealthCheck("external_services", status, message, details, datetime.utcnow(), response_time)


def determine_overall_health(health_checks: List[HealthCheck]) -> HealthStatus:
    """Determine overall system health from individual checks."""
    if any(hc.status == HealthStatus.CRITICAL for hc in health_checks):
        return HealthStatus.CRITICAL
    elif any(hc.status == HealthStatus.WARNING for hc in health_checks):
        return HealthStatus.WARNING
    elif any(hc.status == HealthStatus.UNKNOWN for hc in health_checks):
        return HealthStatus.WARNING  # Treat unknown as warning
    else:
        return HealthStatus.HEALTHY


# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

@celery_app.task(bind=True, name="monitoring.collect_system_metrics")
def collect_system_metrics(self) -> Dict[str, Any]:
    """Collect comprehensive system performance metrics."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Collecting system performance metrics")
    
    collection_time = datetime.utcnow()
    
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1.0)
        cpu_times = psutil.cpu_times_percent(interval=None)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        # Network metrics
        network_io = psutil.net_io_counters()
        
        # Process metrics
        process_count = len(psutil.pids())
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        # Boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = collection_time - boot_time
        
        system_metrics = {
            "timestamp": collection_time.isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "user": cpu_times.user,
                "system": cpu_times.system,
                "idle": cpu_times.idle,
                "iowait": getattr(cpu_times, 'iowait', 0),
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True)
            },
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "percent": memory.percent,
                "buffers_gb": getattr(memory, 'buffers', 0) / (1024**3),
                "cached_gb": getattr(memory, 'cached', 0) / (1024**3)
            },
            "swap": {
                "total_gb": swap.total / (1024**3),
                "used_gb": swap.used / (1024**3),
                "free_gb": swap.free / (1024**3),
                "percent": swap.percent
            },
            "disk": {
                "total_gb": disk_usage.total / (1024**3),
                "used_gb": disk_usage.used / (1024**3),
                "free_gb": disk_usage.free / (1024**3),
                "percent": (disk_usage.used / disk_usage.total) * 100,
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0,
                "read_count": disk_io.read_count if disk_io else 0,
                "write_count": disk_io.write_count if disk_io else 0
            },
            "network": {
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv,
                "errors_in": network_io.errin,
                "errors_out": network_io.errout,
                "drops_in": network_io.dropin,
                "drops_out": network_io.dropout
            },
            "system": {
                "process_count": process_count,
                "load_average_1min": load_avg[0],
                "load_average_5min": load_avg[1],
                "load_average_15min": load_avg[2],
                "boot_time": boot_time.isoformat(),
                "uptime_seconds": uptime.total_seconds(),
                "platform": platform.platform(),
                "python_version": platform.python_version()
            },
            "collector_task_id": task_id
        }
        
        logger.info(f"[{task_id}] System metrics collected successfully")
        return system_metrics
        
    except Exception as e:
        logger.error(f"[{task_id}] Failed to collect system metrics: {e}")
        return {
            "timestamp": collection_time.isoformat(),
            "error": str(e),
            "collector_task_id": task_id
        }


@celery_app.task(bind=True, name="monitoring.collect_celery_metrics")
def collect_celery_metrics(self) -> Dict[str, Any]:
    """Collect Celery-specific performance metrics."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Collecting Celery performance metrics")
    
    collection_time = datetime.utcnow()
    
    try:
        # In production, use actual Celery inspect methods
        # inspect = celery_app.control.inspect()
        # stats = inspect.stats() or {}
        # active_tasks = inspect.active() or {}
        # scheduled_tasks = inspect.scheduled() or {}
        # reserved_tasks = inspect.reserved() or {}
        
        # Simulated Celery metrics
        worker_count = random.randint(3, 10)
        workers = {f"worker{i}@hostname": {
            "pool": {"max-concurrency": random.randint(4, 16)},
            "rusage": {
                "utime": random.uniform(100, 1000),
                "stime": random.uniform(50, 500),
                "maxrss": random.randint(100000, 500000)
            },
            "total": {
                "tasks.active": random.randint(0, 10),
                "tasks.processed": random.randint(1000, 10000),
                "tasks.failed": random.randint(10, 100),
                "tasks.retried": random.randint(50, 200)
            }
        } for i in range(1, worker_count + 1)}
        
        # Aggregate metrics
        total_active = sum(w["total"]["tasks.active"] for w in workers.values())
        total_processed = sum(w["total"]["tasks.processed"] for w in workers.values())
        total_failed = sum(w["total"]["tasks.failed"] for w in workers.values())
        total_retried = sum(w["total"]["tasks.retried"] for w in workers.values())
        
        # Queue metrics (simulated)
        queue_metrics = {
            "celery": {"length": random.randint(0, 50), "consumers": random.randint(2, 8)},
            "priority": {"length": random.randint(0, 20), "consumers": random.randint(1, 4)},
            "batch": {"length": random.randint(0, 100), "consumers": random.randint(2, 6)},
            "background": {"length": random.randint(10, 200), "consumers": random.randint(4, 12)}
        }
        
        total_queue_length = sum(q["length"] for q in queue_metrics.values())
        
        celery_metrics = {
            "timestamp": collection_time.isoformat(),
            "workers": {
                "count": worker_count,
                "details": workers,
                "total_concurrency": sum(w["pool"]["max-concurrency"] for w in workers.values())
            },
            "tasks": {
                "active": total_active,
                "processed": total_processed,
                "failed": total_failed,
                "retried": total_retried,
                "success_rate": (total_processed - total_failed) / total_processed if total_processed > 0 else 0,
                "retry_rate": total_retried / total_processed if total_processed > 0 else 0
            },
            "queues": {
                "total_length": total_queue_length,
                "queue_details": queue_metrics,
                "avg_queue_depth": total_queue_length / len(queue_metrics) if queue_metrics else 0
            },
            "performance": {
                "avg_task_processing_time_seconds": random.uniform(1, 10),
                "tasks_per_second": random.uniform(5, 50),
                "worker_utilization_percent": random.uniform(60, 95)
            },
            "collector_task_id": task_id
        }
        
        logger.info(f"[{task_id}] Celery metrics collected successfully")
        return celery_metrics
        
    except Exception as e:
        logger.error(f"[{task_id}] Failed to collect Celery metrics: {e}")
        return {
            "timestamp": collection_time.isoformat(),
            "error": str(e),
            "collector_task_id": task_id
        }


# =============================================================================
# ALERTING AND NOTIFICATIONS
# =============================================================================

@celery_app.task(bind=True, name="monitoring.evaluate_alerts")
def evaluate_alerts(self, metrics: Dict[str, Any], alert_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate alert rules against collected metrics."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Evaluating {len(alert_rules)} alert rules")
    
    evaluation_time = datetime.utcnow()
    triggered_alerts = []
    
    for rule in alert_rules:
        try:
            alert_result = evaluate_single_alert_rule(rule, metrics)
            if alert_result["triggered"]:
                triggered_alerts.append(alert_result)
        except Exception as e:
            logger.error(f"[{task_id}] Failed to evaluate alert rule {rule.get('name', 'unknown')}: {e}")
    
    # Send notifications for triggered alerts
    notification_results = []
    for alert in triggered_alerts:
        if alert["severity"] in ["critical", "warning"]:
            notification_result = send_alert_notification.delay(alert)
            notification_results.append(notification_result.id)
    
    alert_evaluation = {
        "evaluation_time": evaluation_time.isoformat(),
        "total_rules_evaluated": len(alert_rules),
        "triggered_alerts_count": len(triggered_alerts),
        "triggered_alerts": triggered_alerts,
        "notification_tasks": notification_results,
        "evaluator_task_id": task_id
    }
    
    if triggered_alerts:
        logger.warning(f"[{task_id}] Alert evaluation complete: {len(triggered_alerts)} alerts triggered")
    else:
        logger.info(f"[{task_id}] Alert evaluation complete: no alerts triggered")
    
    return alert_evaluation


def evaluate_single_alert_rule(rule: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single alert rule against metrics."""
    rule_name = rule.get("name", "unnamed_rule")
    metric_path = rule.get("metric_path", "")
    operator = rule.get("operator", "gt")
    threshold = rule.get("threshold", 0)
    severity = rule.get("severity", "warning")
    
    # Extract metric value using path
    metric_value = get_metric_value_by_path(metrics, metric_path)
    
    # Evaluate condition
    triggered = False
    if metric_value is not None:
        if operator == "gt" and metric_value > threshold:
            triggered = True
        elif operator == "lt" and metric_value < threshold:
            triggered = True
        elif operator == "eq" and metric_value == threshold:
            triggered = True
        elif operator == "gte" and metric_value >= threshold:
            triggered = True
        elif operator == "lte" and metric_value <= threshold:
            triggered = True
    
    alert_result = {
        "rule_name": rule_name,
        "metric_path": metric_path,
        "metric_value": metric_value,
        "operator": operator,
        "threshold": threshold,
        "triggered": triggered,
        "severity": severity,
        "message": rule.get("message", f"{rule_name} alert triggered"),
        "evaluated_at": datetime.utcnow().isoformat()
    }
    
    return alert_result


def get_metric_value_by_path(metrics: Dict[str, Any], path: str) -> Optional[Union[int, float]]:
    """Extract metric value using dot notation path."""
    try:
        current = metrics
        for part in path.split("."):
            current = current[part]
        return current if isinstance(current, (int, float)) else None
    except (KeyError, TypeError):
        return None


@celery_app.task(bind=True, name="monitoring.send_alert_notification")
def send_alert_notification(self, alert: Dict[str, Any]) -> Dict[str, Any]:
    """Send notification for triggered alert."""
    task_id = self.request.id
    severity = alert.get("severity", "warning")
    rule_name = alert.get("rule_name", "unknown")
    
    logger.warning(f"[{task_id}] Sending {severity} alert notification: {rule_name}")
    
    # Simulate notification sending
    time.sleep(random.uniform(0.2, 0.8))
    
    notification_channels = []
    if severity == "critical":
        notification_channels = ["email", "slack", "pagerduty", "sms"]
    elif severity == "warning":
        notification_channels = ["email", "slack"]
    else:
        notification_channels = ["slack"]
    
    notification_result = {
        "alert": alert,
        "notification_channels": notification_channels,
        "sent_at": datetime.utcnow().isoformat(),
        "notification_id": f"notif_{random.randint(100000, 999999)}",
        "status": "sent",
        "sender_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Alert notification sent via {', '.join(notification_channels)}")
    return notification_result


# =============================================================================
# MONITORING ORCHESTRATION
# =============================================================================

@celery_app.task(bind=True, name="monitoring.full_monitoring_cycle")
def full_monitoring_cycle(self, monitoring_config: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a complete monitoring cycle with health checks, metrics, and alerting."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting full monitoring cycle")
    
    cycle_start = datetime.utcnow()
    
    # Step 1: System Health Check
    health_check_result = system_health_check.apply_async().get()
    
    # Step 2: Collect System Metrics
    system_metrics_result = collect_system_metrics.apply_async().get()
    
    # Step 3: Collect Celery Metrics
    celery_metrics_result = collect_celery_metrics.apply_async().get()
    
    # Step 4: Evaluate Alerts
    alert_rules = monitoring_config.get("alert_rules", get_default_alert_rules())
    combined_metrics = {
        "system": system_metrics_result,
        "celery": celery_metrics_result,
        "health": health_check_result
    }
    
    alert_evaluation_result = evaluate_alerts.apply_async([combined_metrics, alert_rules]).get()
    
    cycle_end = datetime.utcnow()
    cycle_duration = (cycle_end - cycle_start).total_seconds()
    
    monitoring_cycle_result = {
        "cycle_id": f"monitoring_{task_id}",
        "cycle_start": cycle_start.isoformat(),
        "cycle_end": cycle_end.isoformat(),
        "cycle_duration_seconds": cycle_duration,
        "health_check": health_check_result,
        "system_metrics": system_metrics_result,
        "celery_metrics": celery_metrics_result,
        "alert_evaluation": alert_evaluation_result,
        "overall_status": health_check_result.get("overall_status", "unknown"),
        "coordinator_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Full monitoring cycle complete in {cycle_duration:.1f}s")
    return monitoring_cycle_result


def get_default_alert_rules() -> List[Dict[str, Any]]:
    """Get default alert rules for system monitoring."""
    return [
        {
            "name": "high_cpu_usage",
            "metric_path": "system.cpu.percent",
            "operator": "gt",
            "threshold": 80,
            "severity": "warning",
            "message": "CPU usage is above 80%"
        },
        {
            "name": "critical_cpu_usage",
            "metric_path": "system.cpu.percent",
            "operator": "gt",
            "threshold": 95,
            "severity": "critical",
            "message": "CPU usage is critically high (>95%)"
        },
        {
            "name": "high_memory_usage",
            "metric_path": "system.memory.percent",
            "operator": "gt",
            "threshold": 85,
            "severity": "warning",
            "message": "Memory usage is above 85%"
        },
        {
            "name": "critical_memory_usage",
            "metric_path": "system.memory.percent",
            "operator": "gt",
            "threshold": 95,
            "severity": "critical",
            "message": "Memory usage is critically high (>95%)"
        },
        {
            "name": "high_disk_usage",
            "metric_path": "system.disk.percent",
            "operator": "gt",
            "threshold": 85,
            "severity": "warning",
            "message": "Disk usage is above 85%"
        },
        {
            "name": "high_queue_depth",
            "metric_path": "celery.queues.total_length",
            "operator": "gt",
            "threshold": 500,
            "severity": "warning",
            "message": "Total queue depth is high (>500)"
        },
        {
            "name": "low_task_success_rate",
            "metric_path": "celery.tasks.success_rate",
            "operator": "lt",
            "threshold": 0.95,
            "severity": "critical",
            "message": "Task success rate is below 95%"
        },
        {
            "name": "no_active_workers",
            "metric_path": "celery.workers.count",
            "operator": "eq",
            "threshold": 0,
            "severity": "critical",
            "message": "No active Celery workers detected"
        }
    ]


@celery_app.task(bind=True, name="monitoring.generate_monitoring_report")
def generate_monitoring_report(self, monitoring_data: Dict[str, Any], report_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive monitoring report."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Generating monitoring report")
    
    # Extract key metrics and trends
    health_status = monitoring_data.get("health_check", {}).get("overall_status", "unknown")
    triggered_alerts = monitoring_data.get("alert_evaluation", {}).get("triggered_alerts", [])
    
    # System summary
    system_metrics = monitoring_data.get("system_metrics", {})
    system_summary = {
        "cpu_usage": system_metrics.get("cpu", {}).get("percent", 0),
        "memory_usage": system_metrics.get("memory", {}).get("percent", 0),
        "disk_usage": system_metrics.get("disk", {}).get("percent", 0),
        "uptime_hours": system_metrics.get("system", {}).get("uptime_seconds", 0) / 3600
    }
    
    # Celery summary
    celery_metrics = monitoring_data.get("celery_metrics", {})
    celery_summary = {
        "active_workers": celery_metrics.get("workers", {}).get("count", 0),
        "active_tasks": celery_metrics.get("tasks", {}).get("active", 0),
        "success_rate": celery_metrics.get("tasks", {}).get("success_rate", 0),
        "total_queue_depth": celery_metrics.get("queues", {}).get("total_length", 0)
    }
    
    # Alert summary
    alert_summary = {
        "total_alerts": len(triggered_alerts),
        "critical_alerts": sum(1 for a in triggered_alerts if a.get("severity") == "critical"),
        "warning_alerts": sum(1 for a in triggered_alerts if a.get("severity") == "warning"),
        "alert_details": triggered_alerts
    }
    
    monitoring_report = {
        "report_id": f"report_{task_id}",
        "generated_at": datetime.utcnow().isoformat(),
        "report_period": report_config.get("period", "current"),
        "overall_health": health_status,
        "system_summary": system_summary,
        "celery_summary": celery_summary,
        "alert_summary": alert_summary,
        "recommendations": generate_monitoring_recommendations(monitoring_data),
        "raw_data": monitoring_data if report_config.get("include_raw_data", False) else None,
        "generator_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Monitoring report generated")
    return monitoring_report


def generate_monitoring_recommendations(monitoring_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate recommendations based on monitoring data."""
    recommendations = []
    
    # System recommendations
    system_metrics = monitoring_data.get("system_metrics", {})
    cpu_usage = system_metrics.get("cpu", {}).get("percent", 0)
    memory_usage = system_metrics.get("memory", {}).get("percent", 0)
    
    if cpu_usage > 80:
        recommendations.append({
            "type": "performance",
            "priority": "high" if cpu_usage > 90 else "medium",
            "message": f"CPU usage is high ({cpu_usage:.1f}%). Consider scaling up or optimizing workloads."
        })
    
    if memory_usage > 80:
        recommendations.append({
            "type": "performance",
            "priority": "high" if memory_usage > 90 else "medium",
            "message": f"Memory usage is high ({memory_usage:.1f}%). Consider adding memory or optimizing memory usage."
        })
    
    # Celery recommendations
    celery_metrics = monitoring_data.get("celery_metrics", {})
    worker_count = celery_metrics.get("workers", {}).get("count", 0)
    queue_depth = celery_metrics.get("queues", {}).get("total_length", 0)
    success_rate = celery_metrics.get("tasks", {}).get("success_rate", 1.0)
    
    if worker_count < 3:
        recommendations.append({
            "type": "scaling",
            "priority": "medium",
            "message": f"Only {worker_count} active workers. Consider adding more workers for better throughput."
        })
    
    if queue_depth > 100:
        recommendations.append({
            "type": "scaling",
            "priority": "high" if queue_depth > 500 else "medium",
            "message": f"High queue depth ({queue_depth}). Consider adding workers or optimizing task processing."
        })
    
    if success_rate < 0.95:
        recommendations.append({
            "type": "reliability",
            "priority": "high",
            "message": f"Task success rate is low ({success_rate:.1%}). Investigate task failures and improve error handling."
        })
    
    return recommendations
