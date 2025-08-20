# Testing & Validation Guide

This guide provides comprehensive testing scenarios for all **actually implemented** workflows in the Enterprise Celery Sample Application. Use the Swagger UI at `http://localhost:8000/docs` to test these endpoints interactively.

## 🚀 Quick Start Testing

### Prerequisites
1. Ensure all services are running:
   ```bash
   docker compose up -d redis
   celery -A app.tasks.celery_app worker --loglevel=info &
   celery -A app.tasks.celery_app beat --loglevel=info &
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Access Swagger UI: http://localhost:8000/docs
3. Check system health: http://localhost:8000/health

### 🔍 **Available API Categories**
- **Users**: `/api/v1/users` - User management and relationships
- **Groups**: `/api/v1/groups` - Group management and hierarchies  
- **Computers**: `/api/v1/computers` - Asset management and monitoring
- **Incidents**: `/api/v1/incidents` - Events and incident management
- **Tasks**: `/api/v1/tasks` - Celery task execution and monitoring
- **Monitoring**: `/api/v1/monitoring` - System health and metrics

---

## 📋 Implemented Workflows & Testing Scenarios

## 1. User Management Workflows

### 1.1 User CRUD Operations

#### Test Scenario: Create New User
```http
POST /api/v1/users/
```

**Sample Payload**:
```json
{
  "username": "jane.doe",
  "email": "jane.doe@company.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "department": "Engineering",
  "position": "Software Engineer",
  "phone": "+1-555-0123",
  "is_active": true
}
```

#### Test Scenario: Get User with Relationships
```http
GET /api/v1/users/1
```

**Expected Response**: Includes manager, subordinates, and group memberships

#### Test Scenario: User Group Management
```http
POST /api/v1/users/{user_id}/groups
```

**Sample Payload**:
```json
{
  "group_id": 2
}
```

### 1.2 User Hierarchy Navigation

#### Test Scenario: Get User Subordinates
```http
GET /api/v1/users/{user_id}/subordinates
```

---

## 2. Group Management Workflows

### 2.1 Group Operations

#### Test Scenario: Create Group Hierarchy
```http
POST /api/v1/groups/
```

**Sample Payload**:
```json
{
  "name": "Development Team",
  "description": "Software development team",
  "group_type": "department",
  "parent_group_id": 1,
  "is_active": true
}
```

#### Test Scenario: Get Group Members
```http
GET /api/v1/groups/{group_id}/members
```

#### Test Scenario: Get Group Hierarchy
```http
GET /api/v1/groups/hierarchy/{group_id}
```

---

## 3. Computer Asset Management

### 3.1 Asset CRUD Operations

#### Test Scenario: Register New Computer
```http
POST /api/v1/computers/
```

**Sample Payload**:
```json
{
  "hostname": "dev-laptop-001",
  "ip_address": "192.168.1.100",
  "mac_address": "00:11:22:33:44:55",
  "computer_type": "laptop",
  "os_type": "windows",
  "os_version": "Windows 11",
  "manufacturer": "Dell",
  "model": "XPS 13",
  "cpu": "Intel i7-1165G7",
  "memory_gb": 16,
  "storage_gb": 512,
  "purchase_date": "2024-01-15",
  "warranty_expiry": "2027-01-15",
  "location": "New York Office",
  "owner_id": 1,
  "status": "active"
}
```

#### Test Scenario: Get Computer by Hostname
```http
GET /api/v1/computers/hostname/{hostname}
```

#### Test Scenario: Bulk Computer Updates
```http
POST /api/v1/computers/bulk/update
```

**Sample Payload**:
```json
{
  "updates": [
    {
      "computer_id": 1,
      "location": "Remote",
      "status": "active"
    },
    {
      "computer_id": 2,
      "os_version": "Windows 11 22H2",
      "last_seen": "2024-01-20T10:00:00Z"
    }
  ]
}
```

### 3.2 Asset Reporting

#### Test Scenario: Get Asset Report
```http
GET /api/v1/computers/reports/assets
```

#### Test Scenario: Get Performance Metrics
```http
GET /api/v1/computers/metrics/performance?limit=10
```

---

## 4. Incident & Event Management

### 4.1 Event Operations

#### Test Scenario: Create System Event
```http
POST /api/v1/incidents/events
```

**Sample Payload**:
```json
{
  "event_type": "security",
  "severity": "warning",
  "source": "Security Monitor",
  "title": "Failed login attempt",
  "description": "Multiple failed login attempts detected",
  "raw_data": "{\"attempts\": 5, \"ip\": \"192.168.1.100\"}",
  "computer_id": 1,
  "user_id": 2,
  "occurred_at": "2024-01-20T10:30:00Z"
}
```

#### Test Scenario: Get Event with Details
```http
GET /api/v1/incidents/events/1
```

**Expected Response**: Includes computer, user, and child events

#### Test Scenario: Process Event
```http
PUT /api/v1/incidents/events/{event_id}/process
```

### 4.2 Incident Management

#### Test Scenario: Create Incident
```http
POST /api/v1/incidents/incidents
```

**Sample Payload**:
```json
{
  "title": "Database Connection Issues",
  "description": "Users unable to connect to database",
  "severity": 2,
  "priority": "high",
  "category": "infrastructure",
  "status": "open",
  "reporter_id": 1,
  "affected_computer_id": 5
}
```

#### Test Scenario: Assign Incident
```http
PUT /api/v1/incidents/incidents/{incident_id}/assign
```

**Sample Payload**:
```json
{
  "assignee_id": 3
}
```

#### Test Scenario: Update Incident Status
```http
PUT /api/v1/incidents/incidents/{incident_id}/status
```

**Sample Payload**:
```json
{
  "status": "in_progress",
  "resolution_notes": "Investigation started"
}
```

### 4.3 Analytics & Reporting

#### Test Scenario: Get Event Analytics
```http
GET /api/v1/incidents/analytics/events?days=30
```

#### Test Scenario: Get Incident Analytics
```http
GET /api/v1/incidents/analytics/incidents?days=7
```

---

## 5. Celery Task Management

### 5.1 Available Task Operations

#### Test Scenario: List Available Tasks
```http
GET /api/v1/tasks/
```

#### Test Scenario: Get Registered Tasks
```http
GET /api/v1/tasks/registered
```

#### Test Scenario: Check Worker Status
```http
GET /api/v1/tasks/workers
```

### 5.2 Cache Operations via Celery

#### Test Scenario: Set Cache Value
```http
POST /api/v1/tasks/cache/set?key=test_key&value=test_value&ttl=3600
```

#### Test Scenario: Get Cache Value
```http
POST /api/v1/tasks/cache/get?key=test_key
```

#### Test Scenario: Bulk Cache Operations
```http
POST /api/v1/tasks/cache/bulk-set
```

**Sample Payload**:
```json
[
  {"key": "user_1", "value": "{\"name\": \"John\"}", "ttl": 300},
  {"key": "user_2", "value": "{\"name\": \"Jane\"}", "ttl": 300}
]
```

#### Test Scenario: Cache Warm-up
```http
POST /api/v1/tasks/cache/warm-up
```

**Sample Payload**:
```json
[
  {"pattern": "user_*", "action": "preload"},
  {"pattern": "group_*", "action": "refresh"}
]
```

### 5.3 CRUD Operations via Celery

#### Test Scenario: Create User via Task
```http
POST /api/v1/tasks/crud/create-user
```

**Sample Payload**:
```json
{
  "username": "task.user",
  "email": "task.user@example.com",
  "first_name": "Task",
  "last_name": "User"
}
```

#### Test Scenario: Sync Computer Data
```http
POST /api/v1/tasks/crud/sync-computer
```

**Sample Payload**:
```json
{
  "hostname": "server-001",
  "monitoring_data": {
    "cpu_usage": 75.5,
    "memory_usage": 80.2,
    "disk_usage": 45.0
  }
}
```

#### Test Scenario: Batch Update Computers
```http
POST /api/v1/tasks/crud/batch-update-computers
```

**Sample Payload**:
```json
[
  {"computer_id": 1, "status": "maintenance"},
  {"computer_id": 2, "last_seen": "2024-01-20T12:00:00Z"}
]
```

#### Test Scenario: Process Event via Task
```http
POST /api/v1/tasks/crud/process-event
```

**Sample Payload**:
```json
{
  "event_type": "system",
  "severity": "info",
  "source": "System Monitor",
  "title": "Scheduled maintenance completed",
  "computer_id": 1
}
```

### 5.4 Task Monitoring

#### Test Scenario: Get Task Result
```http
GET /api/v1/tasks/result/{task_id}
```

#### Test Scenario: Revoke Task
```http
POST /api/v1/tasks/result/{task_id}/revoke?terminate=false
```

#### Test Scenario: Demo Workflow
```http
POST /api/v1/tasks/demo/workflow
```

---

## 6. System Monitoring & Health

### 6.1 Health Checks

#### Test Scenario: Basic Health Check
```http
GET /health
```

**Expected Response**: Basic health status

#### Test Scenario: Detailed System Health
```http
GET /api/v1/monitoring/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery_workers": 2,
  "pending_tasks": 0,
  "system_load": "normal",
  "memory_usage": 45.2,
  "disk_usage": 67.8
}
```

### 6.2 System Metrics

#### Test Scenario: Get System Metrics
```http
GET /api/v1/monitoring/metrics/system
```

#### Test Scenario: Get Performance Metrics
```http
GET /api/v1/monitoring/metrics/performance?hours=24
```

### 6.3 Alerts & Notifications

#### Test Scenario: Get System Alerts
```http
GET /api/v1/monitoring/alerts?severity=warning
```

#### Test Scenario: Get Real-time Status
```http
GET /api/v1/monitoring/status/realtime
```

### 6.4 Dashboard Data

#### Test Scenario: Get Dashboard Overview
```http
GET /api/v1/monitoring/dashboard
```

**Expected Response**: Comprehensive dashboard data including counts, metrics, and recent activity



---

## 🧪 Testing Strategies

### 1. Sequential Testing Approach
Execute workflows in logical order:

#### **Phase 1: System Health**
```bash
# 1. Check basic system status
curl http://localhost:8000/health

# 2. Verify Redis connectivity
docker compose exec redis redis-cli ping

# 3. Check detailed monitoring
curl http://localhost:8000/api/v1/monitoring/health
```

#### **Phase 2: Core CRUD Operations**
```bash
# 1. Test user creation and retrieval
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","first_name":"Test","last_name":"User"}'

# 2. Test computer registration
curl -X POST "http://localhost:8000/api/v1/computers/" \
  -H "Content-Type: application/json" \
  -d '{"hostname":"test-pc","status":"active","computer_type":"laptop"}'

# 3. Test group creation
curl -X POST "http://localhost:8000/api/v1/groups/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Group","description":"Testing group","group_type":"department"}'
```

#### **Phase 3: Relationship Testing**
```bash
# 1. Test user with relationships
curl http://localhost:8000/api/v1/users/1

# 2. Test group members
curl http://localhost:8000/api/v1/groups/1/members

# 3. Test computer ownership
curl http://localhost:8000/api/v1/computers/1
```

#### **Phase 4: Incident Management**
```bash
# 1. Create events
curl -X POST "http://localhost:8000/api/v1/incidents/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"system","severity":"info","source":"Test","title":"Test Event"}'

# 2. Create incidents
curl -X POST "http://localhost:8000/api/v1/incidents/incidents" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Incident","severity":3,"priority":"medium","status":"open"}'

# 3. Check analytics
curl "http://localhost:8000/api/v1/incidents/analytics/events?days=7"
```

#### **Phase 5: Celery Task Testing**
```bash
# 1. Check available tasks
curl http://localhost:8000/api/v1/tasks/

# 2. Test cache operations
curl -X POST "http://localhost:8000/api/v1/tasks/cache/set?key=test&value=testvalue&ttl=300"

# 3. Test CRUD tasks
curl -X POST "http://localhost:8000/api/v1/tasks/crud/create-user" \
  -H "Content-Type: application/json" \
  -d '{"username":"taskuser","email":"task@example.com"}'
```

### 2. Load Testing Examples

#### **Concurrent User Operations**
```bash
# Test concurrent user creation
for i in {1..5}; do
  curl -X POST "http://localhost:8000/api/v1/users/" \
    -H "Content-Type: application/json" \
    -d '{"username":"load_user_'$i'","email":"load'$i'@test.com","first_name":"Load","last_name":"User'$i'"}' &
done
wait
```

#### **Bulk Computer Registration**
```bash
# Test bulk computer operations
curl -X POST "http://localhost:8000/api/v1/computers/bulk/update" \
  -H "Content-Type: application/json" \
  -d '{"updates":[{"computer_id":1,"status":"active"},{"computer_id":2,"status":"maintenance"}]}'
```

### 3. Error Scenario Testing

#### **Invalid Payloads**
```bash
# Test missing required fields
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{"email":"incomplete@test.com"}'

# Test invalid data types
curl -X POST "http://localhost:8000/api/v1/computers/" \
  -H "Content-Type: application/json" \
  -d '{"hostname":123,"status":"invalid_status"}'
```

#### **Non-existent Resource Access**
```bash
# Test accessing non-existent user
curl http://localhost:8000/api/v1/users/99999

# Test accessing non-existent group
curl http://localhost:8000/api/v1/groups/99999
```

### 4. Performance Monitoring

#### **Response Time Measurement**
```bash
# Time API responses
time curl -s http://localhost:8000/api/v1/users/ > /dev/null
time curl -s http://localhost:8000/api/v1/computers/reports/assets > /dev/null
```

#### **Task Performance**
```bash
# Monitor task execution time
TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/demo/workflow" | jq -r '.task_id')
curl "http://localhost:8000/api/v1/tasks/result/$TASK_ID"
```

---

## 📊 Validation Criteria

### Response Time Targets (Realistic)
- **Basic CRUD Operations**: < 200ms
  - `GET /api/v1/users/`, `POST /api/v1/computers/`
- **Relationship Queries**: < 500ms
  - `GET /api/v1/users/1` (with relationships)
- **Analytics Endpoints**: < 1 second
  - `GET /api/v1/incidents/analytics/events`
- **Simple Celery Tasks**: < 3 seconds
  - Cache operations, CRUD tasks
- **Bulk Operations**: < 10 seconds
  - `POST /api/v1/computers/bulk/update`

### Success Metrics
- **API Response Rate**: > 99% success (2xx status codes)
- **Database Connectivity**: 100% uptime during testing
- **Redis Cache**: Available and responsive
- **Celery Workers**: At least 1 active worker
- **Task Completion**: > 95% of submitted tasks complete successfully

### Data Validation
- **Required Fields**: All mandatory fields validated by Pydantic
- **Data Types**: Proper type validation (strings, integers, dates)
- **Relationships**: Foreign key constraints respected
- **Unique Constraints**: Usernames, hostnames, etc. properly validated

### Error Handling Validation
- **HTTP Status Codes**: 
  - `200` for successful GET requests
  - `201` for successful POST requests
  - `404` for non-existent resources
  - `422` for validation errors
  - `500` for server errors
- **Error Response Format**: Consistent JSON error responses
- **Validation Messages**: Clear, actionable error descriptions

---

## 🔧 Troubleshooting

### System Health Issues

#### **1. Redis Connection Problems**
```bash
# Check Redis container status
docker compose ps

# Check Redis logs
docker compose logs redis

# Test Redis connectivity
docker compose exec redis redis-cli ping

# Restart Redis if needed
docker compose restart redis
```

#### **2. Database Connection Issues**
```bash
# Check if database file exists
ls -la celery_showcase.db

# Test database connectivity via API
curl http://localhost:8000/api/v1/users/ | head -5
```

#### **3. Celery Worker Problems**
```bash
# Check if workers are running
celery -A app.tasks.celery_app inspect active

# Check worker statistics
celery -A app.tasks.celery_app inspect stats

# Check registered tasks
curl http://localhost:8000/api/v1/tasks/registered

# Restart workers if needed
pkill -f "celery.*worker"
celery -A app.tasks.celery_app worker --loglevel=info &
```

#### **4. API Server Issues**
```bash
# Check if FastAPI is running
curl http://localhost:8000/health

# Check detailed system health
curl http://localhost:8000/api/v1/monitoring/health

# Check server logs
tail -f /var/log/uvicorn.log  # or wherever logs are stored
```

### Data Issues

#### **5. Relationship Loading Errors**
```bash
# Test specific user relationship loading
curl http://localhost:8000/api/v1/users/1 | jq '.manager'
curl http://localhost:8000/api/v1/users/1 | jq '.subordinates'
curl http://localhost:8000/api/v1/users/1 | jq '.groups'
```

#### **6. Validation Errors**
```bash
# Test with invalid payload to check validation
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}' | jq '.detail'
```

### Performance Issues

#### **7. Slow Response Times**
```bash
# Profile specific endpoints
time curl -s http://localhost:8000/api/v1/computers/reports/assets > /dev/null
time curl -s http://localhost:8000/api/v1/incidents/analytics/events > /dev/null

# Check system metrics
curl http://localhost:8000/api/v1/monitoring/metrics/system | jq '.memory_usage'
```

### Debug Mode
Enable detailed logging:
```bash
# Set environment variables for debugging
export CELERY_LOG_LEVEL=DEBUG
export FASTAPI_LOG_LEVEL=DEBUG

# Restart services with debug logging
celery -A app.tasks.celery_app worker --loglevel=debug &
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### Quick Health Check Script
```bash
#!/bin/bash
echo "🔍 SYSTEM HEALTH CHECK"
echo "======================"

# 1. Check Redis
echo -n "Redis: "
docker compose exec redis redis-cli ping 2>/dev/null && echo "✅ OK" || echo "❌ FAILED"

# 2. Check API
echo -n "API: "
curl -s http://localhost:8000/health >/dev/null && echo "✅ OK" || echo "❌ FAILED"

# 3. Check Celery
echo -n "Celery: "
curl -s http://localhost:8000/api/v1/tasks/workers | grep -q "workers" && echo "✅ OK" || echo "❌ FAILED"

# 4. Check Database
echo -n "Database: "
curl -s http://localhost:8000/api/v1/users/ >/dev/null && echo "✅ OK" || echo "❌ FAILED"

echo "======================"
```

---

## 📈 Available Monitoring Endpoints

### Real-time System Information
- **Basic Health**: `GET /health`
- **Detailed Health**: `GET /api/v1/monitoring/health`
- **System Metrics**: `GET /api/v1/monitoring/metrics/system`
- **Performance Metrics**: `GET /api/v1/monitoring/metrics/performance`
- **System Alerts**: `GET /api/v1/monitoring/alerts`
- **Real-time Status**: `GET /api/v1/monitoring/status/realtime`
- **Dashboard Data**: `GET /api/v1/monitoring/dashboard`

### Task Monitoring
- **Available Tasks**: `GET /api/v1/tasks/`
- **Worker Status**: `GET /api/v1/tasks/workers`
- **Task Results**: `GET /api/v1/tasks/result/{task_id}`

### Data Analytics
- **Event Analytics**: `GET /api/v1/incidents/analytics/events`
- **Incident Analytics**: `GET /api/v1/incidents/analytics/incidents`
- **Asset Reports**: `GET /api/v1/computers/reports/assets`
- **Performance Reports**: `GET /api/v1/computers/metrics/performance`

**💡 Use these endpoints to build custom monitoring dashboards or integrate with existing monitoring solutions like Grafana, Prometheus, or Datadog.**
