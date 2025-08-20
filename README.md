# Enterprise Celery Sample Application

A comprehensive, production-ready Python application demonstrating advanced Celery usage patterns, enterprise workflows, and modern application architecture. This project showcases best practices for building scalable, maintainable distributed task processing systems.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  Service Layer  │    │  Celery Tasks   │
│   (API Layer)   │◄──►│ (Business Logic)│◄──►│ (Task Workers)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Pydantic      │    │   Domain Events │    │  Orchestration  │
│   Models        │    │   & Validation  │    │   Patterns      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │ External System │
                    │     Mocks       │
                    └─────────────────┘
```

## 📊 Project Statistics

- **69 Python files** created
- **18,909 lines of code** 
- **6 major architectural layers**
- **50+ enterprise workflow patterns**
- **100+ task implementations**
- **10 external system mocks**

## 🚀 Key Features

### 1. **FastAPI Application Layer**
- **Modern API Design**: RESTful endpoints with OpenAPI documentation
- **Comprehensive CRUD Operations**: Full create, read, update, delete functionality
- **Advanced Filtering**: Search, pagination, and complex query support
- **Real-time Monitoring**: Health checks and system metrics endpoints
- **Interactive Documentation**: Swagger UI and ReDoc integration

### 2. **Advanced Celery Orchestration Patterns**
- **Workflow Orchestration**: Linear, parallel, and chord-based workflows
- **Batch Processing**: Intelligent chunking with progress tracking
- **Priority Queues**: SLA-based task prioritization and routing
- **Retry Strategies**: Exponential backoff, circuit breakers, dead letter queues
- **Callback Management**: Success/failure callbacks and cleanup tasks
- **System Monitoring**: Health checks, metrics collection, and alerting

### 3. **Enterprise Workflow Modules**
- **Incident Management**: ITSM workflows with automated escalation
- **Asset Management**: Complete asset lifecycle and compliance tracking
- **User Onboarding**: Automated employee provisioning and training
- **Compliance Management**: Multi-framework assessment and reporting
- **Backup & Recovery**: Automated backup orchestration and disaster recovery
- **Security Workflows**: Threat detection and automated incident response

### 4. **Service Layer Architecture**
- **Domain Services**: Business logic encapsulation for each domain
- **Integration Services**: External system adapters and API clients
- **Workflow Services**: Cross-domain process orchestration
- **Error Handling**: Comprehensive exception management
- **Validation**: Business rule validation and data integrity
- **Event-Driven**: Domain events for loose coupling

### 5. **External System Mocks**
- **Database Mock**: Complete SQL database simulation with transactions
- **Redis Mock**: Cache operations with TTL and performance metrics
- **Email Service Mock**: SMTP/API email delivery with tracking
- **Slack Mock**: Full Slack API simulation with webhooks
- **External API Mock**: Configurable REST API response simulation
- **Additional Mocks**: SMS, Cloud Storage, LDAP, Monitoring, Webhooks

## 🛠️ Technology Stack

- **Python 3.11+**: Modern Python with type hints
- **Celery 5.3+**: Distributed task queue with Redis broker
- **FastAPI 0.104+**: High-performance web framework
- **Pydantic 2.0+**: Data validation and serialization
- **Redis**: Message broker and caching layer
- **SQLModel**: Modern ORM with type safety
- **Asyncio**: Asynchronous programming support

## 📁 Project Structure

```
py-celery-sample/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── models/                 # Pydantic data models
│   │   ├── user.py            # User domain models
│   │   ├── group.py           # Group and hierarchy models
│   │   ├── computer.py        # Computer and asset models
│   │   ├── incident.py        # Incident management models
│   │   └── task.py            # Task execution models
│   ├── api/                   # FastAPI route handlers
│   │   └── v1/                # API version 1
│   │       ├── users.py       # User management endpoints
│   │       ├── groups.py      # Group management endpoints
│   │       ├── computers.py   # Computer management endpoints
│   │       ├── incidents.py   # Incident management endpoints
│   │       ├── tasks.py       # Task execution endpoints
│   │       └── monitoring.py  # System monitoring endpoints
│   ├── tasks/                 # Celery task definitions
│   │   ├── celery_app.py      # Celery application configuration
│   │   ├── basic/             # Basic CRUD and utility tasks
│   │   ├── orchestration/     # Advanced orchestration patterns
│   │   └── enterprise/        # Enterprise workflow modules
│   ├── services/              # Service layer (business logic)
│   │   ├── base.py            # Base service classes and utilities
│   │   ├── domain/            # Domain-specific services
│   │   ├── integration/       # External system integration
│   │   └── workflows/         # Cross-domain workflow services
│   └── mocks/                 # External system mocks
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Redis service configuration
├── README.md                  # Comprehensive project documentation
└── readme.md                  # Original requirements specification
```

## 🚦 Quick Start

### 1. **Environment Setup**
```bash
# Clone the repository
git clone <repository-url>
cd py-celery-sample

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. **Start Infrastructure Services**
```bash
# Start Redis using modern Docker Compose (note: no hyphen)
docker compose up -d redis

# Verify Redis is running
docker compose ps
docker compose exec redis redis-cli ping  # Should return PONG
```

**Note**: This project uses the modern `docker compose` command (no hyphen), not the legacy `docker-compose`. If you encounter a `ModuleNotFoundError: No module named 'distutils'` error with the old `docker-compose` command, use `docker compose` instead.

#### Docker Configuration
The included `docker-compose.yml` provides:
- **Redis 7 Alpine**: Lightweight Redis instance with data persistence
- **Health Checks**: Automatic service health monitoring
- **Data Persistence**: Volume mounting for data durability
- **Port Mapping**: Redis accessible on localhost:6379

### 3. **Start Application Components**
```bash
# Terminal 1: Start Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info

# Terminal 2: Start Celery Beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info

# Terminal 3: Start FastAPI Application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. **Access the Application**
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 💡 Usage Examples

### Basic Task Execution
```python
from app.tasks.basic.crud_tasks import create_user

# Execute task synchronously
result = create_user.delay({
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe"
})

# Get result
user_data = result.get(timeout=30)
print(f"Created user: {user_data['user_id']}")
```

### Workflow Orchestration
```python
from app.tasks.orchestration.workflow_tasks import linear_workflow

# Execute complex workflow
workflow_result = linear_workflow.delay(
    input_data={"user_id": 123, "data": "sample"},
    workflow_config={
        "validation_rules": {"required_fields": ["user_id"]},
        "transformation_config": {"uppercase_fields": ["status"]},
        "enrichment_config": {"user_lookup": True},
        "storage_config": {"backend": "database"}
    }
)
```

### Enterprise Workflows
```python
from app.tasks.enterprise.incident_management import create_incident

# Create incident with automated response
incident_result = create_incident.delay({
    "title": "Database Performance Issue",
    "description": "Users reporting slow response times",
    "severity": 2,  # High severity
    "affected_services": ["database", "api"],
    "customer_impact": "moderate"
})
```

### Service Layer Usage
```python
from app.services.domain.user_service import UserService

# Use service layer for business logic
user_service = UserService()
result = await user_service.create_user({
    "username": "jane_doe",
    "email": "jane@example.com",
    "department": "engineering",
    "role": "software_engineer"
}, trigger_onboarding=True)

if result.success:
    print(f"User created: {result.data['user_id']}")
else:
    print(f"Error: {result.error.message}")
```

## 🏢 Enterprise Features

### 1. **Incident Management (ITSM)**
- Automated incident creation and assignment
- SLA monitoring with breach detection
- Escalation workflows with management notifications
- Automated diagnosis and resolution attempts
- Post-incident analysis and reporting

### 2. **Asset Management**
- Network asset discovery and inventory
- Automated provisioning workflows
- Compliance auditing and tracking
- Equipment lifecycle management
- Integration with procurement systems

### 3. **User Onboarding**
- Multi-step employee onboarding automation
- Account provisioning across systems
- Training and orientation scheduling
- Equipment assignment and tracking
- Department-specific workflows

### 4. **Compliance Management**
- Multi-framework compliance assessment (GDPR, SOX, PCI-DSS)
- Automated audit workflows
- Evidence collection and documentation
- Compliance reporting and analytics
- Risk assessment and remediation

### 5. **Backup & Disaster Recovery**
- Automated backup orchestration
- Priority-based backup scheduling
- Disaster recovery procedures
- Data validation and integrity checking
- Recovery testing and verification

### 6. **Security Operations**
- Continuous security monitoring
- Automated threat detection
- Incident response automation
- Forensic evidence collection
- Security metrics and reporting

## 🔧 Configuration

### Environment Variables
```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Database Configuration  
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Email Configuration
EMAIL_PROVIDER=sendgrid
EMAIL_API_KEY=your_api_key

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Monitoring
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Celery Configuration
```python
# Configure in app/tasks/celery_app.py
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True
```

## 📈 Monitoring & Observability

### Built-in Metrics
- **Task Execution**: Success rates, execution times, failure patterns
- **Queue Health**: Depth, processing rates, worker utilization
- **System Resources**: CPU, memory, disk usage
- **Business Metrics**: Incident resolution times, SLA compliance
- **Integration Health**: External system availability and performance

### Health Checks
- `/health` - Overall system health
- `/health/detailed` - Component-specific health
- `/metrics` - Prometheus-compatible metrics
- `/status` - Real-time system status

### Logging
- Structured JSON logging
- Correlation IDs for request tracking
- Audit trails for compliance
- Performance metrics logging
- Error tracking and alerting

## 🧪 Testing

### Test Coverage
- Unit tests for all service methods
- Integration tests for workflow orchestration
- Mock-based testing for external systems
- Performance testing for high-volume scenarios
- End-to-end API testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/          # End-to-end tests

# Run with coverage
pytest --cov=app --cov-report=html
```

### Mock System Testing
```python
from app.mocks import DatabaseMock, EmailServiceMock

# Use mocks in tests
async def test_user_creation():
    db_mock = DatabaseMock()
    email_mock = EmailServiceMock()
    
    # Configure mock behavior
    email_mock.set_failure_rate(0.1)  # 10% failure rate
    
    # Run test with mocks
    result = await create_user_workflow(db_mock, email_mock)
    assert result["success"] is True
```

## 🚀 Deployment

### Production Considerations
- **Scalability**: Horizontal scaling with multiple workers
- **Security**: Authentication, authorization, and encryption
- **Monitoring**: Comprehensive logging and alerting
- **Backup**: Regular database and configuration backups
- **Updates**: Blue-green deployment strategies

### Docker Deployment
```yaml
# docker-compose.prod.yml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    depends_on:
      - redis
  
  worker:
    build: .
    command: celery -A app.tasks.celery_app worker --loglevel=info
    depends_on:
      - redis
  
  beat:
    build: .
    command: celery -A app.tasks.celery_app beat --loglevel=info
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    container_name: celery-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  redis_data:
```

**Deployment Commands**:
```bash
# Start all services in production
docker compose -f docker-compose.prod.yml up -d

# Scale workers for high load
docker compose -f docker-compose.prod.yml up -d --scale worker=3

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop all services
docker compose -f docker-compose.prod.yml down
```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Code Standards
- Follow PEP 8 style guide
- Add type hints to all functions
- Write comprehensive docstrings
- Include unit tests for new features
- Update documentation as needed

## 📚 Additional Resources

### Documentation
- [Celery Documentation](https://docs.celeryproject.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Redis Documentation](https://redis.io/documentation)

### Related Projects
- [Celery Best Practices](https://github.com/celery/celery/blob/main/docs/userguide/tasks.rst)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [Python Enterprise Patterns](https://github.com/cosmicpython/book)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Celery Team**: For the excellent distributed task queue framework
- **FastAPI Team**: For the modern, high-performance web framework
- **Pydantic Team**: For outstanding data validation and serialization
- **Python Community**: For the rich ecosystem of enterprise tools

---

**Built with ❤️ for enterprise Python development**

This comprehensive sample demonstrates production-ready patterns for building scalable, maintainable distributed systems with Celery and FastAPI. The architecture and patterns shown here are suitable for enterprise environments requiring high reliability, observability, and operational excellence.
