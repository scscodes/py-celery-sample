"""
Enterprise Incident Management Workflows

This module provides comprehensive ITSM (IT Service Management) workflows for incident
handling, escalation, resolution tracking, and post-incident analysis in enterprise environments.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import random
import time
from enum import Enum
from dataclasses import dataclass

from celery import chain, group, chord
from app.tasks.celery_app import celery_app
from app.tasks.orchestration.callbacks_tasks import CallbackConfig, with_callbacks
from app.tasks.orchestration.priority_tasks import Priority, PriorityTaskConfig

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels following ITIL standards."""
    CRITICAL = 1    # System down, major business impact
    HIGH = 2        # Significant impact, workaround available
    MEDIUM = 3      # Moderate impact, standard timeline
    LOW = 4         # Minor impact, when resources available


class IncidentStatus(Enum):
    """Incident lifecycle status."""
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class EscalationLevel(Enum):
    """Escalation levels for incident management."""
    L1_SUPPORT = "L1"
    L2_SUPPORT = "L2"
    L3_ENGINEERING = "L3"
    MANAGEMENT = "management"
    EXECUTIVE = "executive"


@dataclass
class IncidentContext:
    """Incident context and metadata."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.NEW
    assigned_to: Optional[str] = None
    escalation_level: EscalationLevel = EscalationLevel.L1_SUPPORT
    affected_services: List[str] = None
    customer_impact: str = "unknown"
    business_impact: str = "unknown"
    created_at: datetime = None
    sla_target: Optional[datetime] = None
    
    def __post_init__(self):
        if self.affected_services is None:
            self.affected_services = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.sla_target is None:
            self.sla_target = self.calculate_sla_target()
    
    def calculate_sla_target(self) -> datetime:
        """Calculate SLA target based on severity."""
        sla_hours = {
            IncidentSeverity.CRITICAL: 1,
            IncidentSeverity.HIGH: 4,
            IncidentSeverity.MEDIUM: 24,
            IncidentSeverity.LOW: 72
        }
        return self.created_at + timedelta(hours=sla_hours[self.severity])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "escalation_level": self.escalation_level.value,
            "affected_services": self.affected_services,
            "customer_impact": self.customer_impact,
            "business_impact": self.business_impact,
            "created_at": self.created_at.isoformat(),
            "sla_target": self.sla_target.isoformat() if self.sla_target else None
        }


# =============================================================================
# INCIDENT CREATION AND INITIAL PROCESSING
# =============================================================================

@celery_app.task(bind=True, name="incident.create_incident")
@with_callbacks(CallbackConfig(
    success_callbacks=["log_success", "send_slack"],
    failure_callbacks=["log_failure", "escalate_to_ops"],
    audit_enabled=True
))
def create_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new incident and initiate response workflow."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Creating new incident")
    
    # Create incident context
    incident = IncidentContext(
        incident_id=incident_data.get("incident_id", f"INC-{random.randint(100000, 999999)}"),
        title=incident_data["title"],
        description=incident_data["description"],
        severity=IncidentSeverity(incident_data.get("severity", 3)),
        affected_services=incident_data.get("affected_services", []),
        customer_impact=incident_data.get("customer_impact", "unknown"),
        business_impact=incident_data.get("business_impact", "unknown")
    )
    
    # Determine initial assignment and priority
    priority = get_priority_for_severity(incident.severity)
    initial_assignee = assign_initial_responder(incident)
    
    # Update incident with assignment
    incident.assigned_to = initial_assignee
    incident.status = IncidentStatus.ASSIGNED
    
    # Store incident in system (simulated)
    store_incident_data.delay(incident.to_dict())
    
    # Send initial notifications
    notify_incident_created.delay(incident.to_dict())
    
    # Schedule SLA monitoring
    monitor_incident_sla.apply_async(
        args=[incident.incident_id],
        countdown=60  # Check SLA every minute
    )
    
    # Initiate response workflow based on severity
    if incident.severity == IncidentSeverity.CRITICAL:
        initiate_critical_incident_response.delay(incident.to_dict())
    
    # Automatic troubleshooting for known patterns
    initiate_automated_diagnosis.delay(incident.to_dict())
    
    result = {
        "incident": incident.to_dict(),
        "initial_assignee": initial_assignee,
        "priority": priority.value,
        "workflow_initiated": True,
        "created_by_task": task_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"[{task_id}] Incident {incident.incident_id} created successfully")
    return result


def get_priority_for_severity(severity: IncidentSeverity) -> Priority:
    """Map incident severity to task priority."""
    severity_priority_map = {
        IncidentSeverity.CRITICAL: Priority.CRITICAL,
        IncidentSeverity.HIGH: Priority.HIGH,
        IncidentSeverity.MEDIUM: Priority.NORMAL,
        IncidentSeverity.LOW: Priority.LOW
    }
    return severity_priority_map[severity]


def assign_initial_responder(incident: IncidentContext) -> str:
    """Assign initial responder based on incident characteristics."""
    # Simulate intelligent assignment based on various factors
    if incident.severity == IncidentSeverity.CRITICAL:
        return random.choice(["senior_engineer_1", "senior_engineer_2", "lead_engineer"])
    elif "database" in incident.description.lower():
        return random.choice(["db_admin_1", "db_admin_2"])
    elif "network" in incident.description.lower():
        return random.choice(["network_admin_1", "network_admin_2"])
    else:
        return random.choice(["support_agent_1", "support_agent_2", "support_agent_3"])


# =============================================================================
# INCIDENT RESPONSE AND ESCALATION
# =============================================================================

@celery_app.task(bind=True, name="incident.initiate_critical_incident_response")
def initiate_critical_incident_response(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Initiate immediate response for critical incidents."""
    task_id = self.request.id
    incident_id = incident_data["incident_id"]
    
    logger.critical(f"[{task_id}] Initiating critical incident response for {incident_id}")
    
    # Immediate actions for critical incidents
    response_actions = []
    
    # 1. Page on-call engineers
    page_oncall_engineers.delay(incident_data)
    response_actions.append("on_call_paging")
    
    # 2. Create war room
    war_room_result = create_incident_war_room.delay(incident_data)
    response_actions.append("war_room_creation")
    
    # 3. Notify executive team
    notify_executive_team.delay(incident_data)
    response_actions.append("executive_notification")
    
    # 4. Enable enhanced monitoring
    enable_enhanced_monitoring.delay(incident_data["affected_services"])
    response_actions.append("enhanced_monitoring")
    
    # 5. Prepare rollback options
    prepare_rollback_options.delay(incident_data)
    response_actions.append("rollback_preparation")
    
    # 6. Start status page updates
    start_status_page_updates.delay(incident_data)
    response_actions.append("status_page_updates")
    
    # Schedule escalation check
    check_critical_incident_progress.apply_async(
        args=[incident_id],
        countdown=300  # Check progress every 5 minutes
    )
    
    response_summary = {
        "incident_id": incident_id,
        "response_level": "critical",
        "actions_initiated": response_actions,
        "response_time": datetime.utcnow().isoformat(),
        "coordinator_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Critical incident response initiated for {incident_id}")
    return response_summary


@celery_app.task(bind=True, name="incident.escalate_incident")
def escalate_incident(self, incident_id: str, escalation_reason: str, current_level: str) -> Dict[str, Any]:
    """Escalate incident to next level of support."""
    task_id = self.request.id
    logger.warning(f"[{task_id}] Escalating incident {incident_id}: {escalation_reason}")
    
    # Determine next escalation level
    escalation_map = {
        EscalationLevel.L1_SUPPORT.value: EscalationLevel.L2_SUPPORT,
        EscalationLevel.L2_SUPPORT.value: EscalationLevel.L3_ENGINEERING,
        EscalationLevel.L3_ENGINEERING.value: EscalationLevel.MANAGEMENT,
        EscalationLevel.MANAGEMENT.value: EscalationLevel.EXECUTIVE
    }
    
    current_enum = EscalationLevel(current_level)
    next_level = escalation_map.get(current_enum, EscalationLevel.EXECUTIVE)
    
    # Get incident data
    incident_data = get_incident_data.apply_async([incident_id]).get()
    
    # Update incident escalation level
    incident_data["escalation_level"] = next_level.value
    incident_data["escalated_at"] = datetime.utcnow().isoformat()
    incident_data["escalation_reason"] = escalation_reason
    
    # Reassign based on new escalation level
    new_assignee = get_assignee_for_escalation_level(next_level, incident_data)
    incident_data["assigned_to"] = new_assignee
    
    # Update incident record
    store_incident_data.delay(incident_data)
    
    # Notify new assignee and stakeholders
    notify_incident_escalation.delay(incident_data, escalation_reason)
    
    # Additional actions based on escalation level
    if next_level == EscalationLevel.MANAGEMENT:
        # Management escalation actions
        create_management_briefing.delay(incident_data)
        schedule_escalation_review.delay(incident_id)
    
    elif next_level == EscalationLevel.EXECUTIVE:
        # Executive escalation actions
        create_executive_summary.delay(incident_data)
        initiate_crisis_management.delay(incident_data)
    
    escalation_result = {
        "incident_id": incident_id,
        "previous_level": current_level,
        "new_level": next_level.value,
        "new_assignee": new_assignee,
        "escalation_reason": escalation_reason,
        "escalated_at": datetime.utcnow().isoformat(),
        "escalator_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Incident {incident_id} escalated to {next_level.value}")
    return escalation_result


def get_assignee_for_escalation_level(level: EscalationLevel, incident_data: Dict[str, Any]) -> str:
    """Get appropriate assignee based on escalation level."""
    if level == EscalationLevel.L2_SUPPORT:
        return random.choice(["l2_engineer_1", "l2_engineer_2", "l2_engineer_3"])
    elif level == EscalationLevel.L3_ENGINEERING:
        return random.choice(["senior_engineer_1", "principal_engineer", "team_lead"])
    elif level == EscalationLevel.MANAGEMENT:
        return random.choice(["engineering_manager", "ops_manager", "service_owner"])
    elif level == EscalationLevel.EXECUTIVE:
        return random.choice(["director_engineering", "vp_engineering", "cto"])
    else:
        return "default_assignee"


# =============================================================================
# AUTOMATED DIAGNOSIS AND RESOLUTION
# =============================================================================

@celery_app.task(bind=True, name="incident.initiate_automated_diagnosis")
def initiate_automated_diagnosis(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run automated diagnosis and potential resolution steps."""
    task_id = self.request.id
    incident_id = incident_data["incident_id"]
    
    logger.info(f"[{task_id}] Starting automated diagnosis for {incident_id}")
    
    # Run parallel diagnostic checks
    diagnostic_tasks = group([
        check_system_health.s(incident_data),
        analyze_logs.s(incident_data),
        check_dependencies.s(incident_data),
        run_connectivity_tests.s(incident_data),
        check_resource_utilization.s(incident_data)
    ])
    
    # Execute diagnostics and aggregate results
    diagnostic_chord = chord(diagnostic_tasks)(
        aggregate_diagnostic_results.s(incident_data)
    )
    
    # Schedule automated resolution attempts if safe
    if is_safe_for_automated_resolution(incident_data):
        schedule_automated_resolution.apply_async(
            args=[incident_id],
            countdown=300  # Wait 5 minutes for manual intervention first
        )
    
    diagnosis_result = {
        "incident_id": incident_id,
        "diagnostic_tasks_started": len(diagnostic_tasks.tasks),
        "diagnostic_chord_id": diagnostic_chord.id,
        "automated_resolution_scheduled": is_safe_for_automated_resolution(incident_data),
        "started_at": datetime.utcnow().isoformat(),
        "initiator_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Automated diagnosis initiated for {incident_id}")
    return diagnosis_result


@celery_app.task(bind=True, name="incident.check_system_health")
def check_system_health(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check overall system health related to the incident."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Checking system health for incident")
    
    # Simulate health checks
    time.sleep(random.uniform(1, 3))
    
    affected_services = incident_data.get("affected_services", [])
    health_results = {}
    
    for service in affected_services:
        # Simulate service health check
        is_healthy = random.choice([True, False, False])  # 33% healthy
        response_time = random.uniform(100, 5000) if not is_healthy else random.uniform(50, 200)
        
        health_results[service] = {
            "healthy": is_healthy,
            "response_time_ms": response_time,
            "error_rate": random.uniform(0, 50) if not is_healthy else random.uniform(0, 2)
        }
    
    overall_health = all(h["healthy"] for h in health_results.values())
    
    return {
        "check_type": "system_health",
        "overall_healthy": overall_health,
        "service_health": health_results,
        "checked_at": datetime.utcnow().isoformat(),
        "checker_task_id": task_id
    }


@celery_app.task(bind=True, name="incident.analyze_logs")
def analyze_logs(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze system logs for incident-related patterns."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Analyzing logs for incident patterns")
    
    # Simulate log analysis
    time.sleep(random.uniform(2, 5))
    
    # Simulate finding various log patterns
    log_patterns = []
    if random.random() < 0.7:  # 70% chance of finding error patterns
        log_patterns.extend([
            {"pattern": "ERROR", "count": random.randint(50, 500), "service": "api-service"},
            {"pattern": "TIMEOUT", "count": random.randint(10, 100), "service": "database"},
            {"pattern": "CONNECTION_REFUSED", "count": random.randint(5, 50), "service": "cache"}
        ])
    
    if random.random() < 0.5:  # 50% chance of finding warning patterns
        log_patterns.extend([
            {"pattern": "HIGH_MEMORY_USAGE", "count": random.randint(20, 200), "service": "worker"},
            {"pattern": "SLOW_QUERY", "count": random.randint(10, 80), "service": "database"}
        ])
    
    # Correlate with incident timing
    incident_created = datetime.fromisoformat(incident_data["created_at"].replace('Z', '+00:00'))
    time_window_start = incident_created - timedelta(hours=1)
    
    return {
        "check_type": "log_analysis",
        "time_window_start": time_window_start.isoformat(),
        "time_window_end": incident_created.isoformat(),
        "patterns_found": log_patterns,
        "total_error_events": sum(p["count"] for p in log_patterns if "ERROR" in p["pattern"]),
        "analysis_confidence": random.uniform(0.6, 0.95),
        "analyzed_at": datetime.utcnow().isoformat(),
        "analyzer_task_id": task_id
    }


@celery_app.task(bind=True, name="incident.check_dependencies")
def check_dependencies(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check status of external dependencies."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Checking external dependencies")
    
    # Simulate dependency checks
    time.sleep(random.uniform(1, 4))
    
    dependencies = [
        "payment_gateway", "user_service", "notification_service",
        "analytics_api", "third_party_api", "cdn_provider"
    ]
    
    dependency_status = {}
    for dep in dependencies:
        is_available = random.choice([True, True, False])  # 67% available
        
        dependency_status[dep] = {
            "available": is_available,
            "response_time_ms": random.uniform(100, 2000) if is_available else None,
            "last_error": None if is_available else f"Connection timeout to {dep}",
            "checked_at": datetime.utcnow().isoformat()
        }
    
    failed_dependencies = [dep for dep, status in dependency_status.items() if not status["available"]]
    
    return {
        "check_type": "dependency_check",
        "total_dependencies": len(dependencies),
        "available_dependencies": len(dependencies) - len(failed_dependencies),
        "failed_dependencies": failed_dependencies,
        "dependency_details": dependency_status,
        "overall_dependency_health": len(failed_dependencies) == 0,
        "checked_at": datetime.utcnow().isoformat(),
        "checker_task_id": task_id
    }


@celery_app.task(bind=True, name="incident.run_connectivity_tests")
def run_connectivity_tests(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run network connectivity tests."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Running connectivity tests")
    
    # Simulate connectivity tests
    time.sleep(random.uniform(1, 3))
    
    connectivity_tests = {
        "internal_dns": {"passed": random.choice([True, False]), "latency_ms": random.uniform(1, 50)},
        "external_dns": {"passed": random.choice([True, False]), "latency_ms": random.uniform(10, 100)},
        "database_connection": {"passed": random.choice([True, False]), "latency_ms": random.uniform(5, 200)},
        "cache_connection": {"passed": random.choice([True, False]), "latency_ms": random.uniform(1, 50)},
        "api_gateway": {"passed": random.choice([True, False]), "latency_ms": random.uniform(10, 500)}
    }
    
    passed_tests = sum(1 for test in connectivity_tests.values() if test["passed"])
    total_tests = len(connectivity_tests)
    
    return {
        "check_type": "connectivity_tests",
        "tests_passed": passed_tests,
        "total_tests": total_tests,
        "success_rate": passed_tests / total_tests,
        "test_details": connectivity_tests,
        "tested_at": datetime.utcnow().isoformat(),
        "tester_task_id": task_id
    }


@celery_app.task(bind=True, name="incident.check_resource_utilization")
def check_resource_utilization(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check system resource utilization."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Checking resource utilization")
    
    # Simulate resource checks
    time.sleep(random.uniform(1, 2))
    
    resource_metrics = {
        "cpu_usage_percent": random.uniform(20, 95),
        "memory_usage_percent": random.uniform(30, 90),
        "disk_usage_percent": random.uniform(40, 85),
        "network_utilization_percent": random.uniform(10, 80),
        "active_connections": random.randint(100, 2000),
        "queue_depth": random.randint(0, 500)
    }
    
    # Identify resource constraints
    resource_alerts = []
    if resource_metrics["cpu_usage_percent"] > 80:
        resource_alerts.append("HIGH_CPU_USAGE")
    if resource_metrics["memory_usage_percent"] > 85:
        resource_alerts.append("HIGH_MEMORY_USAGE")
    if resource_metrics["disk_usage_percent"] > 90:
        resource_alerts.append("HIGH_DISK_USAGE")
    if resource_metrics["queue_depth"] > 100:
        resource_alerts.append("HIGH_QUEUE_DEPTH")
    
    return {
        "check_type": "resource_utilization",
        "resource_metrics": resource_metrics,
        "resource_alerts": resource_alerts,
        "resource_pressure": len(resource_alerts) > 0,
        "checked_at": datetime.utcnow().isoformat(),
        "checker_task_id": task_id
    }


@celery_app.task(bind=True, name="incident.aggregate_diagnostic_results")
def aggregate_diagnostic_results(self, diagnostic_results: List[Dict[str, Any]], incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate all diagnostic results and determine recommended actions."""
    task_id = self.request.id
    incident_id = incident_data["incident_id"]
    
    logger.info(f"[{task_id}] Aggregating diagnostic results for {incident_id}")
    
    # Analyze all diagnostic results
    health_issues = []
    recommendations = []
    confidence_scores = []
    
    for result in diagnostic_results:
        check_type = result.get("check_type", "unknown")
        
        if check_type == "system_health" and not result.get("overall_healthy", True):
            health_issues.append("Unhealthy services detected")
            recommendations.append("Restart unhealthy services")
        
        elif check_type == "log_analysis":
            error_count = result.get("total_error_events", 0)
            if error_count > 100:
                health_issues.append(f"High error rate: {error_count} events")
                recommendations.append("Investigate error patterns and apply fixes")
            confidence_scores.append(result.get("analysis_confidence", 0.5))
        
        elif check_type == "dependency_check" and not result.get("overall_dependency_health", True):
            failed_deps = result.get("failed_dependencies", [])
            health_issues.append(f"Failed dependencies: {', '.join(failed_deps)}")
            recommendations.append("Check dependency status and failover if needed")
        
        elif check_type == "connectivity_tests":
            success_rate = result.get("success_rate", 1.0)
            if success_rate < 0.8:
                health_issues.append(f"Connectivity issues: {success_rate:.1%} success rate")
                recommendations.append("Investigate network connectivity issues")
        
        elif check_type == "resource_utilization" and result.get("resource_pressure", False):
            alerts = result.get("resource_alerts", [])
            health_issues.append(f"Resource pressure: {', '.join(alerts)}")
            recommendations.append("Scale resources or optimize resource usage")
    
    # Generate overall assessment
    overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.7
    severity_score = len(health_issues)
    
    # Determine recommended actions based on findings
    if severity_score == 0:
        overall_status = "healthy"
        primary_recommendation = "Monitor for additional symptoms"
    elif severity_score <= 2:
        overall_status = "degraded"
        primary_recommendation = "Apply targeted fixes for identified issues"
    else:
        overall_status = "unhealthy"
        primary_recommendation = "Immediate intervention required"
    
    # Update incident with diagnostic findings
    diagnostic_summary = {
        "diagnostic_completed_at": datetime.utcnow().isoformat(),
        "overall_status": overall_status,
        "health_issues_found": len(health_issues),
        "confidence_score": overall_confidence,
        "primary_recommendation": primary_recommendation
    }
    
    update_incident_diagnostics.delay(incident_id, diagnostic_summary)
    
    aggregated_result = {
        "incident_id": incident_id,
        "diagnostic_summary": diagnostic_summary,
        "health_issues": health_issues,
        "recommendations": recommendations,
        "detailed_results": diagnostic_results,
        "aggregated_at": datetime.utcnow().isoformat(),
        "aggregator_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Diagnostic aggregation complete for {incident_id}: {overall_status}")
    return aggregated_result


def is_safe_for_automated_resolution(incident_data: Dict[str, Any]) -> bool:
    """Determine if incident is safe for automated resolution attempts."""
    severity = IncidentSeverity(incident_data.get("severity", 3))
    
    # Only attempt automated resolution for low/medium severity incidents
    if severity in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH]:
        return False
    
    # Check if affected services are in safe list
    affected_services = incident_data.get("affected_services", [])
    safe_services = ["cache", "monitoring", "analytics", "reporting"]
    
    return all(service in safe_services for service in affected_services)


# =============================================================================
# INCIDENT MONITORING AND SLA TRACKING
# =============================================================================

@celery_app.task(bind=True, name="incident.monitor_incident_sla")
def monitor_incident_sla(self, incident_id: str) -> Dict[str, Any]:
    """Monitor incident SLA compliance and trigger escalations."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Monitoring SLA for incident {incident_id}")
    
    # Get current incident data
    incident_data = get_incident_data.apply_async([incident_id]).get()
    
    if not incident_data:
        logger.warning(f"[{task_id}] Incident {incident_id} not found")
        return {"status": "incident_not_found", "incident_id": incident_id}
    
    current_time = datetime.utcnow()
    sla_target = datetime.fromisoformat(incident_data["sla_target"].replace('Z', '+00:00'))
    time_remaining = (sla_target - current_time).total_seconds()
    
    sla_status = {
        "incident_id": incident_id,
        "current_status": incident_data["status"],
        "sla_target": sla_target.isoformat(),
        "time_remaining_seconds": time_remaining,
        "sla_breach": time_remaining <= 0,
        "monitored_at": current_time.isoformat(),
        "monitor_task_id": task_id
    }
    
    # Check if SLA is breached or at risk
    if time_remaining <= 0:
        # SLA breached
        logger.critical(f"[{task_id}] SLA BREACH: Incident {incident_id} exceeded target")
        handle_sla_breach.delay(incident_id, sla_status)
        
    elif time_remaining <= 1800:  # 30 minutes remaining
        # SLA at risk - send warning
        logger.warning(f"[{task_id}] SLA WARNING: Incident {incident_id} has {time_remaining/60:.1f} minutes remaining")
        send_sla_warning.delay(incident_id, sla_status)
    
    # Continue monitoring if incident is still open
    if incident_data["status"] not in ["resolved", "closed", "cancelled"]:
        monitor_incident_sla.apply_async(
            args=[incident_id],
            countdown=300  # Check again in 5 minutes
        )
    
    return sla_status


@celery_app.task(bind=True, name="incident.handle_sla_breach")
def handle_sla_breach(self, incident_id: str, sla_status: Dict[str, Any]) -> Dict[str, Any]:
    """Handle SLA breach with automatic escalation and notifications."""
    task_id = self.request.id
    logger.critical(f"[{task_id}] Handling SLA breach for incident {incident_id}")
    
    # Get current incident data
    incident_data = get_incident_data.apply_async([incident_id]).get()
    
    # Record SLA breach
    breach_record = {
        "incident_id": incident_id,
        "breach_time": datetime.utcnow().isoformat(),
        "original_sla_target": sla_status["sla_target"],
        "time_overrun_seconds": abs(sla_status["time_remaining_seconds"]),
        "severity": incident_data["severity"],
        "current_assignee": incident_data.get("assigned_to"),
        "escalation_level": incident_data.get("escalation_level")
    }
    
    # Store breach record
    store_sla_breach_record.delay(breach_record)
    
    # Automatic escalation
    escalation_result = escalate_incident.delay(
        incident_id, 
        "SLA breach - automatic escalation", 
        incident_data.get("escalation_level", "L1")
    )
    
    # Send breach notifications
    send_sla_breach_notifications.delay(incident_id, breach_record)
    
    # Schedule management review for critical/high severity breaches
    if IncidentSeverity(incident_data["severity"]) in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH]:
        schedule_management_review.delay(incident_id, breach_record)
    
    breach_response = {
        "incident_id": incident_id,
        "breach_record": breach_record,
        "escalation_task_id": escalation_result.id,
        "notifications_sent": True,
        "management_review_scheduled": IncidentSeverity(incident_data["severity"]) in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH],
        "handled_at": datetime.utcnow().isoformat(),
        "handler_task_id": task_id
    }
    
    logger.info(f"[{task_id}] SLA breach handled for incident {incident_id}")
    return breach_response


# =============================================================================
# SUPPORT TASKS
# =============================================================================

@celery_app.task(bind=True, name="incident.get_incident_data")
def get_incident_data(self, incident_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve incident data from storage."""
    task_id = self.request.id
    
    # Simulate database lookup
    time.sleep(random.uniform(0.1, 0.3))
    
    # In production, this would query actual database
    # For demo, return simulated data
    if random.random() > 0.1:  # 90% success rate
        return {
            "incident_id": incident_id,
            "title": f"Sample incident {incident_id}",
            "description": "Simulated incident data",
            "severity": random.randint(1, 4),
            "status": random.choice(["new", "assigned", "in_progress", "resolved"]),
            "assigned_to": f"engineer_{random.randint(1, 5)}",
            "escalation_level": random.choice(["L1", "L2", "L3"]),
            "affected_services": ["api", "database"],
            "created_at": datetime.utcnow().isoformat(),
            "sla_target": (datetime.utcnow() + timedelta(hours=4)).isoformat()
        }
    return None


@celery_app.task(bind=True, name="incident.store_incident_data")
def store_incident_data(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store incident data to persistent storage."""
    task_id = self.request.id
    
    # Simulate database storage
    time.sleep(random.uniform(0.1, 0.5))
    
    return {
        "stored": True,
        "incident_id": incident_data["incident_id"],
        "stored_at": datetime.utcnow().isoformat(),
        "storage_task_id": task_id
    }


@celery_app.task(bind=True, name="incident.notify_incident_created")
def notify_incident_created(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send notifications for new incident creation."""
    task_id = self.request.id
    
    # Simulate notification sending
    time.sleep(random.uniform(0.2, 0.8))
    
    return {
        "notification_type": "incident_created",
        "incident_id": incident_data["incident_id"],
        "recipients": ["on_call_team", "incident_manager"],
        "channels": ["email", "slack", "sms"],
        "sent_at": datetime.utcnow().isoformat(),
        "sender_task_id": task_id
    }


# Additional support tasks would be implemented here...
# (page_oncall_engineers, create_incident_war_room, etc.)

@celery_app.task(bind=True, name="incident.page_oncall_engineers")
def page_oncall_engineers(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Page on-call engineers for critical incidents."""
    task_id = self.request.id
    
    time.sleep(random.uniform(0.1, 0.3))
    
    return {
        "action": "page_oncall",
        "incident_id": incident_data["incident_id"],
        "engineers_paged": ["oncall_engineer_1", "oncall_engineer_2"],
        "paged_at": datetime.utcnow().isoformat(),
        "pager_task_id": task_id
    }


@celery_app.task(bind=True, name="incident.create_incident_war_room")
def create_incident_war_room(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create war room for critical incident coordination."""
    task_id = self.request.id
    
    time.sleep(random.uniform(0.5, 1.0))
    
    return {
        "action": "war_room_created",
        "incident_id": incident_data["incident_id"],
        "war_room_url": f"https://company.zoom.us/j/{random.randint(1000000000, 9999999999)}",
        "participants_invited": ["incident_commander", "technical_lead", "communications_lead"],
        "created_at": datetime.utcnow().isoformat(),
        "creator_task_id": task_id
    }


# Continue with additional support tasks...
@celery_app.task(bind=True, name="incident.update_incident_diagnostics")
def update_incident_diagnostics(self, incident_id: str, diagnostic_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Update incident with diagnostic findings."""
    task_id = self.request.id
    
    time.sleep(random.uniform(0.1, 0.2))
    
    return {
        "updated": True,
        "incident_id": incident_id,
        "diagnostic_summary": diagnostic_summary,
        "updated_at": datetime.utcnow().isoformat(),
        "updater_task_id": task_id
    }
