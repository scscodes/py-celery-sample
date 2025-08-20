"""
Incident Domain Service

This service handles incident management business logic including incident lifecycle,
escalation management, SLA tracking, and resolution workflows.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.services.base import BaseService, ServiceResult, service_method, ValidationError, NotFoundError
from app.tasks.enterprise.incident_management import (
    create_incident, escalate_incident, initiate_critical_incident_response,
    monitor_incident_sla, initiate_automated_diagnosis
)

logger = logging.getLogger(__name__)


class IncidentService(BaseService):
    """Service for incident management and resolution."""
    
    def __init__(self):
        super().__init__("IncidentService")
        self._sla_thresholds = {
            1: {"response_minutes": 15, "resolution_hours": 1},   # Critical
            2: {"response_minutes": 60, "resolution_hours": 4},   # High  
            3: {"response_minutes": 240, "resolution_hours": 24}, # Medium
            4: {"response_minutes": 1440, "resolution_hours": 72} # Low
        }
    
    @service_method
    async def create_incident(self, incident_data: Dict[str, Any], 
                            auto_assign: bool = True) -> ServiceResult[Dict[str, Any]]:
        """Create a new incident with automatic assignment and SLA setup."""
        
        # Validate incident data
        validation_result = self._validate_incident_data(incident_data)
        if not validation_result.success:
            return validation_result
        
        # Enrich incident data
        enriched_data = self._enrich_incident_data(incident_data)
        
        try:
            # Create incident via enterprise task
            task_result = create_incident.delay(enriched_data)
            incident_result = task_result.get(timeout=30)
            
            # Auto-assign if requested and not already assigned
            if auto_assign and not enriched_data.get("assigned_to"):
                assignment_result = await self._auto_assign_incident(incident_result)
                if assignment_result.success:
                    incident_result.update(assignment_result.data)
            
            # Start SLA monitoring
            if enriched_data.get("severity"):
                monitor_incident_sla.delay(incident_result["incident"]["incident_id"])
            
            # Trigger automated diagnosis for appropriate incidents
            if self._should_run_automated_diagnosis(enriched_data):
                diagnosis_task = initiate_automated_diagnosis.delay(incident_result["incident"])
                incident_result["diagnosis_task_id"] = diagnosis_task.id
            
            # Emit incident created event
            await self._emit_incident_event("incident_created", incident_result)
            
            return ServiceResult.success_result(incident_result)
            
        except Exception as e:
            self.logger.error(f"Failed to create incident: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def escalate_incident(self, incident_id: str, escalation_reason: str,
                              force_escalation: bool = False) -> ServiceResult[Dict[str, Any]]:
        """Escalate incident to next level with proper workflow."""
        
        # Get current incident details
        incident_details = await self._get_incident_details(incident_id)
        if not incident_details:
            return ServiceResult.error_result(
                NotFoundError("Incident", incident_id)
            )
        
        # Check if escalation is warranted
        if not force_escalation:
            escalation_check = self._should_escalate_incident(incident_details, escalation_reason)
            if not escalation_check["should_escalate"]:
                return ServiceResult.error_result(
                    ValidationError(f"Escalation not warranted: {escalation_check['reason']}")
                )
        
        try:
            # Execute escalation
            current_level = incident_details.get("escalation_level", "L1")
            task_result = escalate_incident.delay(incident_id, escalation_reason, current_level)
            escalation_result = task_result.get(timeout=30)
            
            # Handle critical escalations
            if escalation_result.get("new_level") in ["management", "executive"]:
                await self._handle_critical_escalation(incident_id, escalation_result)
            
            # Emit escalation event
            await self._emit_incident_event("incident_escalated", escalation_result)
            
            return ServiceResult.success_result(escalation_result)
            
        except Exception as e:
            self.logger.error(f"Failed to escalate incident {incident_id}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def resolve_incident(self, incident_id: str, resolution_data: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
        """Resolve incident with proper closure workflow."""
        
        # Validate resolution data
        if not resolution_data.get("resolution_summary"):
            return ServiceResult.error_result(
                ValidationError("Resolution summary is required")
            )
        
        try:
            # Get incident details for validation
            incident_details = await self._get_incident_details(incident_id)
            if not incident_details:
                return ServiceResult.error_result(
                    NotFoundError("Incident", incident_id)
                )
            
            # Prepare resolution update
            resolution_update = {
                "status": "resolved",
                "resolution_summary": resolution_data["resolution_summary"],
                "resolved_by": resolution_data.get("resolved_by", "system"),
                "resolved_at": datetime.utcnow().isoformat(),
                "resolution_category": resolution_data.get("category", "other"),
                "follow_up_required": resolution_data.get("follow_up_required", False)
            }
            
            # Update incident (simplified - would use actual update task)
            # update_result = update_incident.delay(incident_id, resolution_update)
            
            # Calculate resolution metrics
            resolution_metrics = self._calculate_resolution_metrics(incident_details, resolution_update)
            
            # Schedule post-resolution activities
            if resolution_data.get("follow_up_required"):
                await self._schedule_follow_up_activities(incident_id, resolution_data)
            
            # Send closure notifications
            await self._send_resolution_notifications(incident_id, incident_details, resolution_update)
            
            result = {
                "incident_id": incident_id,
                "resolution": resolution_update,
                "metrics": resolution_metrics
            }
            
            # Emit resolution event
            await self._emit_incident_event("incident_resolved", result)
            
            return ServiceResult.success_result(result)
            
        except Exception as e:
            self.logger.error(f"Failed to resolve incident {incident_id}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def get_incident_metrics(self, time_range_hours: int = 24) -> ServiceResult[Dict[str, Any]]:
        """Get incident management metrics and KPIs."""
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
            
            # This would query actual incident data in production
            # For demo, return sample metrics
            metrics = {
                "time_range_hours": time_range_hours,
                "total_incidents": 45,
                "open_incidents": 8,
                "resolved_incidents": 37,
                "escalated_incidents": 12,
                "sla_breaches": 3,
                "sla_compliance_rate": 93.3,
                "severity_distribution": {
                    "critical": 2,
                    "high": 8,
                    "medium": 15,
                    "low": 20
                },
                "average_resolution_time_hours": 4.2,
                "average_response_time_minutes": 18,
                "top_incident_categories": [
                    {"category": "network", "count": 12},
                    {"category": "application", "count": 10},
                    {"category": "infrastructure", "count": 8}
                ],
                "metrics_generated_at": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to get incident metrics: {e}")
            return ServiceResult.from_exception(e)
    
    # Helper methods
    
    def _validate_incident_data(self, incident_data: Dict[str, Any]) -> ServiceResult[bool]:
        """Validate incident creation data."""
        errors = []
        
        # Required fields
        required_fields = ["title", "description"]
        for field in required_fields:
            if not incident_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Severity validation
        severity = incident_data.get("severity")
        if severity and severity not in [1, 2, 3, 4]:
            errors.append("Severity must be 1 (Critical), 2 (High), 3 (Medium), or 4 (Low)")
        
        # Service validation
        affected_services = incident_data.get("affected_services", [])
        if affected_services and not isinstance(affected_services, list):
            errors.append("Affected services must be a list")
        
        if errors:
            return ServiceResult.error_result(
                ValidationError(f"Validation failed: {', '.join(errors)}")
            )
        
        return ServiceResult.success_result(True)
    
    def _enrich_incident_data(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich incident data with defaults and computed fields."""
        enriched = incident_data.copy()
        
        # Set defaults
        enriched.setdefault("severity", 3)  # Medium by default
        enriched.setdefault("status", "new")
        enriched.setdefault("created_at", datetime.utcnow().isoformat())
        enriched.setdefault("customer_impact", "unknown")
        enriched.setdefault("business_impact", "unknown")
        
        # Calculate SLA target
        severity = enriched["severity"]
        if severity in self._sla_thresholds:
            sla_hours = self._sla_thresholds[severity]["resolution_hours"]
            sla_target = datetime.utcnow() + timedelta(hours=sla_hours)
            enriched["sla_target"] = sla_target.isoformat()
        
        return enriched
    
    async def _auto_assign_incident(self, incident_result: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
        """Auto-assign incident based on rules."""
        # Simplified auto-assignment logic
        incident = incident_result.get("incident", {})
        severity = incident.get("severity", 3)
        affected_services = incident.get("affected_services", [])
        
        # Assignment logic based on severity and services
        if severity == 1:  # Critical
            assignee = "critical_response_team"
        elif "database" in affected_services:
            assignee = "database_team"
        elif "network" in affected_services:
            assignee = "network_team"
        else:
            assignee = "general_support"
        
        return ServiceResult.success_result({
            "assigned_to": assignee,
            "assignment_reason": "auto_assignment",
            "assigned_at": datetime.utcnow().isoformat()
        })
    
    def _should_run_automated_diagnosis(self, incident_data: Dict[str, Any]) -> bool:
        """Determine if automated diagnosis should be run."""
        # Run for medium and high severity incidents
        severity = incident_data.get("severity", 4)
        return severity <= 3
    
    async def _get_incident_details(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident details (mock implementation)."""
        # In production, this would fetch from database
        return {
            "incident_id": incident_id,
            "severity": 2,
            "status": "in_progress",
            "escalation_level": "L1",
            "created_at": datetime.utcnow().isoformat()
        }
    
    def _should_escalate_incident(self, incident_details: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Determine if incident should be escalated."""
        # Simplified escalation logic
        severity = incident_details.get("severity", 4)
        current_level = incident_details.get("escalation_level", "L1")
        
        # Auto-escalate critical incidents after 1 hour
        if severity == 1 and current_level == "L1":
            return {"should_escalate": True, "reason": "Critical incident auto-escalation"}
        
        # Check SLA breach
        created_at = incident_details.get("created_at")
        if created_at:
            incident_age = (datetime.utcnow() - datetime.fromisoformat(created_at)).total_seconds() / 3600
            sla_threshold = self._sla_thresholds.get(severity, {}).get("resolution_hours", 24)
            
            if incident_age > sla_threshold * 0.8:  # 80% of SLA time
                return {"should_escalate": True, "reason": "Approaching SLA breach"}
        
        return {"should_escalate": True, "reason": reason}  # Allow manual escalation
    
    async def _handle_critical_escalation(self, incident_id: str, escalation_result: Dict[str, Any]):
        """Handle critical escalations with additional workflows."""
        # Trigger critical incident response if escalating to management
        if escalation_result.get("new_level") == "management":
            incident_details = await self._get_incident_details(incident_id)
            initiate_critical_incident_response.delay(incident_details)
    
    def _calculate_resolution_metrics(self, incident_details: Dict[str, Any], resolution: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate resolution metrics."""
        created_at = datetime.fromisoformat(incident_details["created_at"])
        resolved_at = datetime.fromisoformat(resolution["resolved_at"])
        
        resolution_time_hours = (resolved_at - created_at).total_seconds() / 3600
        severity = incident_details.get("severity", 4)
        sla_target_hours = self._sla_thresholds.get(severity, {}).get("resolution_hours", 24)
        
        return {
            "resolution_time_hours": resolution_time_hours,
            "sla_target_hours": sla_target_hours,
            "sla_met": resolution_time_hours <= sla_target_hours,
            "sla_variance_hours": resolution_time_hours - sla_target_hours
        }
    
    async def _schedule_follow_up_activities(self, incident_id: str, resolution_data: Dict[str, Any]):
        """Schedule follow-up activities for resolved incidents."""
        # Implementation for follow-up scheduling
        pass
    
    async def _send_resolution_notifications(self, incident_id: str, incident_details: Dict[str, Any], resolution: Dict[str, Any]):
        """Send notifications about incident resolution."""
        # Implementation for resolution notifications
        pass
    
    async def _emit_incident_event(self, event_type: str, incident_data: Dict[str, Any]):
        """Emit incident-related events."""
        self.logger.info(f"Incident event: {event_type} for incident {incident_data.get('incident_id', 'unknown')}")
