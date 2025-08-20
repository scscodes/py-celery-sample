"""
Service Layer

This module provides a clean business logic layer that orchestrates between the API
endpoints and the underlying Celery tasks. It implements the Service Layer pattern
to encapsulate business rules, validation, and workflow coordination.

Architecture:
============

1. **Base Services** (base.py):
   - Abstract base classes and common patterns
   - Error handling and logging utilities
   - Service registration and dependency injection

2. **Domain Services** (domain/):
   - User management and authentication
   - Group and organizational hierarchy
   - Computer and asset management  
   - Incident and event handling
   - Task orchestration and monitoring

3. **Integration Services** (integration/):
   - External system adapters
   - API client wrappers
   - Data synchronization services
   - Webhook and notification services

4. **Workflow Services** (workflows/):
   - Complex business process orchestration
   - State machine implementations
   - Cross-domain workflow coordination
   - Event-driven process automation

Key Principles:
==============

- **Separation of Concerns**: Clear boundaries between API, business logic, and tasks
- **Dependency Injection**: Services can be easily mocked and tested
- **Event-Driven**: Domain events for loose coupling between services
- **Transaction Management**: Proper handling of distributed transactions
- **Error Handling**: Consistent error handling and logging patterns
- **Validation**: Business rule validation separate from data validation
- **Caching**: Intelligent caching strategies for performance
- **Monitoring**: Built-in metrics and health checks

Usage Example:
=============

```python
from app.services.domain.user_service import UserService
from app.services.workflows.onboarding_service import OnboardingService

# Initialize services (normally done via dependency injection)
user_service = UserService()
onboarding_service = OnboardingService(user_service)

# Create user with business logic
user_result = await user_service.create_user({
    "username": "john.doe",
    "email": "john.doe@company.com",
    "department": "engineering",
    "role": "software_engineer"
})

# Start onboarding workflow
onboarding_result = await onboarding_service.start_onboarding(
    user_id=user_result.user_id,
    onboarding_config={
        "department": "engineering",
        "manager_id": "MGR-001",
        "start_date": "2024-01-15"
    }
)
```
"""

from .base import BaseService, ServiceError, ServiceResult
from .domain import *
from .integration import *
from .workflows import *

__all__ = [
    'BaseService',
    'ServiceError', 
    'ServiceResult'
]
