"""
External System Mocks

This module provides mock implementations of external systems for testing and
development purposes. These mocks simulate the behavior of real external services
without requiring actual connections or API keys.

Available Mock Systems:
======================

1. **DatabaseMock** - Mock database operations
2. **RedisMock** - Mock Redis cache operations  
3. **EmailServiceMock** - Mock email service (SMTP, SendGrid, etc.)
4. **SlackMock** - Mock Slack API integration
5. **SMSMock** - Mock SMS service (Twilio, etc.)
6. **CloudStorageMock** - Mock cloud storage (AWS S3, Azure Blob, etc.)
7. **ExternalAPIMock** - Mock third-party REST APIs
8. **LDAPMock** - Mock LDAP/Active Directory
9. **MonitoringMock** - Mock monitoring systems (DataDog, New Relic, etc.)
10. **WebhookMock** - Mock webhook endpoints

Usage Examples:
==============

```python
from app.mocks import DatabaseMock, EmailServiceMock

# Initialize mocks
db_mock = DatabaseMock()
email_mock = EmailServiceMock()

# Use in tests or development
user_data = await db_mock.create_user({"username": "test", "email": "test@example.com"})
await email_mock.send_email("test@example.com", "Welcome", "Welcome to our service!")
```

Configuration:
=============

Mocks can be configured to simulate various behaviors:

```python
# Configure failure rates
email_mock.set_failure_rate(0.1)  # 10% failure rate

# Configure response delays
api_mock.set_response_delay(0.5, 2.0)  # 0.5-2.0 second delays

# Configure specific responses
api_mock.add_response_mapping("/users/123", {"id": 123, "name": "John Doe"})
```

Environment Integration:
=======================

Mocks automatically detect when they should be used:

```python
import os

# Use mocks in development/testing
if os.getenv("ENVIRONMENT") in ["development", "testing"]:
    from app.mocks import DatabaseMock as Database
else:
    from app.database import Database  # Real implementation
```
"""

from .database_mock import DatabaseMock
from .redis_mock import RedisMock
from .email_service_mock import EmailServiceMock
from .slack_mock import SlackMock
from .sms_mock import SMSMock
from .cloud_storage_mock import CloudStorageMock
from .external_api_mock import ExternalAPIMock
from .ldap_mock import LDAPMock
from .monitoring_mock import MonitoringMock
from .webhook_mock import WebhookMock

__all__ = [
    'DatabaseMock',
    'RedisMock',
    'EmailServiceMock',
    'SlackMock',
    'SMSMock',
    'CloudStorageMock',
    'ExternalAPIMock',
    'LDAPMock',
    'MonitoringMock',
    'WebhookMock'
]
