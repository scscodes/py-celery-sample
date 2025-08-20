"""
Onboarding Workflow Service

This service orchestrates complex employee onboarding workflows that span
multiple domains including user management, asset provisioning, and training.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.services.base import BaseService, ServiceResult, service_method
from app.services.domain.user_service import UserService
from app.services.domain.task_service import TaskService

logger = logging.getLogger(__name__)


class OnboardingService(BaseService):
    """Service for employee onboarding workflow orchestration."""
    
    def __init__(self, user_service: UserService = None, task_service: TaskService = None):
        super().__init__("OnboardingService")
        self._user_service = user_service
        self._task_service = task_service
    
    @service_method
    async def start_onboarding(self, onboarding_data: Dict[str, Any]) -> ServiceResult[Dict[str, Any]]:
        """Start comprehensive employee onboarding workflow."""
        
        try:
            # Create user account
            user_result = await self._user_service.create_user(
                onboarding_data["user_data"], 
                trigger_onboarding=False  # We'll handle the workflow here
            )
            
            if not user_result.success:
                return user_result
            
            # Start onboarding workflow
            workflow_result = await self._task_service.execute_workflow(
                "user_onboarding",
                {
                    "employee_id": user_result.data["user_id"],
                    "onboarding_config": onboarding_data["config"]
                },
                priority="high"
            )
            
            if not workflow_result.success:
                return workflow_result
            
            onboarding_result = {
                "user_id": user_result.data["user_id"],
                "workflow_id": workflow_result.data["workflow_id"],
                "started_at": datetime.utcnow().isoformat(),
                "status": "in_progress"
            }
            
            return ServiceResult.success_result(onboarding_result)
            
        except Exception as e:
            self.logger.error(f"Failed to start onboarding: {e}")
            return ServiceResult.from_exception(e)
