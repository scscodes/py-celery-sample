"""
Task Domain Service

This service handles task orchestration, monitoring, and management business logic
including task execution, progress tracking, result management, and workflow coordination.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.services.base import BaseService, ServiceResult, service_method, ValidationError, NotFoundError
from app.tasks.orchestration.workflow_tasks import linear_workflow, parallel_workflow, chord_workflow
from app.tasks.orchestration.batch_tasks import chunked_batch_processor, progressive_batch_processor
from app.tasks.orchestration.priority_tasks import submit_priority_task, Priority
from app.tasks.enterprise.incident_management import create_incident
from app.tasks.enterprise.user_onboarding import initiate_employee_onboarding

logger = logging.getLogger(__name__)


class TaskService(BaseService):
    """Service for task orchestration and management."""
    
    def __init__(self):
        super().__init__("TaskService")
        self._active_workflows = {}
        self._task_registry = {}
    
    @service_method
    async def execute_workflow(self, workflow_type: str, workflow_data: Dict[str, Any], 
                              priority: str = "normal") -> ServiceResult[Dict[str, Any]]:
        """Execute a workflow with the specified type and data."""
        
        # Validate workflow type
        if not self._is_valid_workflow_type(workflow_type):
            return ServiceResult.error_result(
                ValidationError(f"Invalid workflow type: {workflow_type}")
            )
        
        # Prepare workflow configuration
        workflow_config = self._prepare_workflow_config(workflow_data, priority)
        
        try:
            # Route to appropriate workflow execution
            if workflow_type == "linear":
                task_result = linear_workflow.delay(workflow_data, workflow_config)
            elif workflow_type == "parallel":
                task_result = parallel_workflow.delay(workflow_data, workflow_config)
            elif workflow_type == "chord":
                task_result = chord_workflow.delay(workflow_data, workflow_config)
            elif workflow_type == "incident_management":
                task_result = create_incident.delay(workflow_data)
            elif workflow_type == "user_onboarding":
                task_result = initiate_employee_onboarding.delay(workflow_data)
            else:
                return ServiceResult.error_result(
                    ValidationError(f"Workflow type not implemented: {workflow_type}")
                )
            
            # Track workflow execution
            workflow_execution = {
                "workflow_id": task_result.id,
                "workflow_type": workflow_type,
                "started_at": datetime.utcnow().isoformat(),
                "status": "running",
                "priority": priority,
                "config": workflow_config
            }
            
            self._active_workflows[task_result.id] = workflow_execution
            
            return ServiceResult.success_result(workflow_execution)
            
        except Exception as e:
            self.logger.error(f"Failed to execute {workflow_type} workflow: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def execute_batch_processing(self, batch_data: List[Dict[str, Any]], 
                                     processing_config: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
        """Execute batch processing with intelligent chunking and progress tracking."""
        
        # Validate batch data
        if not batch_data:
            return ServiceResult.error_result(
                ValidationError("Batch data cannot be empty")
            )
        
        batch_size = len(batch_data)
        processing_type = processing_config.get("type", "chunked")
        
        try:
            # Choose appropriate batch processing strategy
            if processing_type == "chunked":
                task_result = chunked_batch_processor.delay(batch_data, processing_config)
            elif processing_type == "progressive":
                task_result = progressive_batch_processor.delay(batch_data, processing_config)
            else:
                return ServiceResult.error_result(
                    ValidationError(f"Invalid processing type: {processing_type}")
                )
            
            # Track batch execution
            batch_execution = {
                "batch_id": task_result.id,
                "batch_size": batch_size,
                "processing_type": processing_type,
                "started_at": datetime.utcnow().isoformat(),
                "status": "processing",
                "config": processing_config
            }
            
            return ServiceResult.success_result(batch_execution)
            
        except Exception as e:
            self.logger.error(f"Failed to execute batch processing: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def submit_priority_task(self, task_name: str, task_data: Dict[str, Any], 
                                  priority_config: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
        """Submit a task with priority scheduling and SLA management."""
        
        # Validate task configuration
        if not self._is_registered_task(task_name):
            return ServiceResult.error_result(
                ValidationError(f"Task not registered: {task_name}")
            )
        
        try:
            # Submit priority task
            task_result = submit_priority_task.delay(
                task_name=task_name,
                task_args=[task_data],
                task_kwargs={},
                config=priority_config
            )
            
            # Track priority task
            priority_execution = {
                "task_id": task_result.id,
                "task_name": task_name,
                "priority": priority_config.get("priority", Priority.NORMAL.value),
                "sla_seconds": priority_config.get("sla_seconds"),
                "submitted_at": datetime.utcnow().isoformat(),
                "status": "queued"
            }
            
            return ServiceResult.success_result(priority_execution)
            
        except Exception as e:
            self.logger.error(f"Failed to submit priority task {task_name}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def get_task_status(self, task_id: str) -> ServiceResult[Dict[str, Any]]:
        """Get current status of a task or workflow."""
        
        try:
            # Check if it's a tracked workflow
            if task_id in self._active_workflows:
                workflow_info = self._active_workflows[task_id]
                
                # Get actual task status from Celery
                from celery.result import AsyncResult
                result = AsyncResult(task_id)
                
                workflow_info.update({
                    "celery_status": result.status,
                    "result": result.result if result.ready() else None,
                    "traceback": result.traceback if result.failed() else None
                })
                
                return ServiceResult.success_result(workflow_info)
            
            # For non-workflow tasks, get basic Celery status
            from celery.result import AsyncResult
            result = AsyncResult(task_id)
            
            task_status = {
                "task_id": task_id,
                "status": result.status,
                "result": result.result if result.ready() else None,
                "traceback": result.traceback if result.failed() else None
            }
            
            return ServiceResult.success_result(task_status)
            
        except Exception as e:
            self.logger.error(f"Failed to get task status for {task_id}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def cancel_task(self, task_id: str, reason: str = "User requested") -> ServiceResult[bool]:
        """Cancel a running task or workflow."""
        
        try:
            from celery.result import AsyncResult
            result = AsyncResult(task_id)
            
            # Revoke the task
            result.revoke(terminate=True)
            
            # Update tracking if it's a workflow
            if task_id in self._active_workflows:
                self._active_workflows[task_id].update({
                    "status": "cancelled",
                    "cancelled_at": datetime.utcnow().isoformat(),
                    "cancellation_reason": reason
                })
            
            self.logger.info(f"Task {task_id} cancelled: {reason}")
            return ServiceResult.success_result(True)
            
        except Exception as e:
            self.logger.error(f"Failed to cancel task {task_id}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def get_workflow_history(self, filters: Dict[str, Any] = None, 
                                  limit: int = 50) -> ServiceResult[List[Dict[str, Any]]]:
        """Get workflow execution history with filtering."""
        
        try:
            # Filter workflows based on criteria
            filtered_workflows = []
            
            for workflow_id, workflow_info in self._active_workflows.items():
                # Apply filters
                if filters:
                    if filters.get("workflow_type") and workflow_info.get("workflow_type") != filters["workflow_type"]:
                        continue
                    if filters.get("status") and workflow_info.get("status") != filters["status"]:
                        continue
                    if filters.get("priority") and workflow_info.get("priority") != filters["priority"]:
                        continue
                
                filtered_workflows.append(workflow_info)
            
            # Sort by start time (newest first) and limit
            sorted_workflows = sorted(
                filtered_workflows,
                key=lambda x: x.get("started_at", ""),
                reverse=True
            )[:limit]
            
            return ServiceResult.success_result(sorted_workflows)
            
        except Exception as e:
            self.logger.error(f"Failed to get workflow history: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def get_system_metrics(self) -> ServiceResult[Dict[str, Any]]:
        """Get task system performance metrics."""
        
        try:
            # Calculate metrics from tracked workflows
            total_workflows = len(self._active_workflows)
            running_workflows = sum(1 for w in self._active_workflows.values() if w.get("status") == "running")
            completed_workflows = sum(1 for w in self._active_workflows.values() if w.get("status") == "completed")
            failed_workflows = sum(1 for w in self._active_workflows.values() if w.get("status") == "failed")
            
            # Calculate average execution time for completed workflows
            completed_times = []
            for workflow in self._active_workflows.values():
                if workflow.get("status") == "completed" and workflow.get("started_at") and workflow.get("completed_at"):
                    start = datetime.fromisoformat(workflow["started_at"])
                    end = datetime.fromisoformat(workflow["completed_at"])
                    completed_times.append((end - start).total_seconds())
            
            avg_execution_time = sum(completed_times) / len(completed_times) if completed_times else 0
            
            metrics = {
                "total_workflows": total_workflows,
                "running_workflows": running_workflows,
                "completed_workflows": completed_workflows,
                "failed_workflows": failed_workflows,
                "success_rate": (completed_workflows / total_workflows) if total_workflows > 0 else 0,
                "average_execution_time_seconds": avg_execution_time,
                "active_task_types": list(set(w.get("workflow_type") for w in self._active_workflows.values())),
                "metrics_timestamp": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return ServiceResult.from_exception(e)
    
    def register_task(self, task_name: str, task_info: Dict[str, Any]) -> None:
        """Register a task for validation and tracking."""
        self._task_registry[task_name] = {
            "registered_at": datetime.utcnow().isoformat(),
            "info": task_info
        }
        self.logger.info(f"Registered task: {task_name}")
    
    def _is_valid_workflow_type(self, workflow_type: str) -> bool:
        """Check if workflow type is supported."""
        valid_types = [
            "linear", "parallel", "chord", 
            "incident_management", "user_onboarding"
        ]
        return workflow_type in valid_types
    
    def _is_registered_task(self, task_name: str) -> bool:
        """Check if task is registered."""
        # For demo, allow any task name
        return True
    
    def _prepare_workflow_config(self, workflow_data: Dict[str, Any], priority: str) -> Dict[str, Any]:
        """Prepare workflow configuration with defaults."""
        return {
            "priority": priority,
            "timeout_seconds": 3600,  # 1 hour default
            "retry_policy": {
                "max_retries": 3,
                "retry_delay": 60
            },
            "validation_rules": workflow_data.get("validation_rules", {}),
            "transformation_config": workflow_data.get("transformation_config", {}),
            "enrichment_config": workflow_data.get("enrichment_config", {}),
            "storage_config": workflow_data.get("storage_config", {})
        }
