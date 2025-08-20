# Celery Implementation Showcase

This guide demonstrates the advanced Celery capabilities implemented in the Enterprise IT Asset & Incident Management system, organized by increasing complexity. Each section includes complete setup, execution, and validation instructions.

## 🛠️ Prerequisites & Tools

**Required:**
- Python 3.8+
- Docker & Docker Compose
- curl
- Access to terminal/bash

**JSON Parsing:** Commands use Python for JSON parsing (universally available). Alternative `jq` commands are provided where helpful.

**Optional Tools:**
```bash
# Install jq for enhanced JSON viewing (optional)
sudo apt install jq  # Ubuntu/Debian
brew install jq      # macOS
```

## 📋 Table of Contents

### [🚀 Level 1: Foundation Showcase](#level-1-foundation-showcase)
- [1.1 Worker Lifecycle Management](#11-worker-lifecycle-management)
- [1.2 Basic Demo Workflow](#12-basic-demo-workflow)
- [1.3 Task Monitoring & Status](#13-task-monitoring--status)

### [🔄 Level 2: Scalable Operations](#level-2-scalable-operations)
- [2.1 Batch Processing Showcase](#21-batch-processing-showcase)
- [2.2 Cache Operations Campaign](#22-cache-operations-campaign)
- [2.3 Concurrent Task Management](#23-concurrent-task-management)

### [🏢 Level 3: Advanced Orchestration](#level-3-advanced-orchestration)
- [3.1 Complex Workflow Patterns](#31-complex-workflow-patterns)
- [3.2 Retry & Error Handling](#32-retry--error-handling)
- [3.3 Priority Queue Management](#33-priority-queue-management)

### [🏭 Level 4: Enterprise Workflows](#level-4-enterprise-workflows)
- [4.1 Continuous Monitoring System](#41-continuous-monitoring-system)
- [4.2 Security & Compliance Automation](#42-security--compliance-automation)
- [4.3 User Onboarding Orchestration](#43-user-onboarding-orchestration)

### [📊 Monitoring & Analytics](#monitoring--analytics)
- [Real-time Dashboards](#real-time-dashboards)
- [Performance Metrics](#performance-metrics)
- [Extended Monitoring Setup](#extended-monitoring-setup)

---

## 🚀 Level 1: Foundation Showcase

*Duration: 5-10 minutes | Complexity: Beginner*

### Prerequisites
```bash
# Ensure all services are running
docker compose up -d redis
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Verify API is accessible
curl http://localhost:8000/health
```

### 1.1 Worker Lifecycle Management

**Demonstrates:** Worker startup, task registration, health monitoring

#### Setup
```bash
# Check current worker status
curl -s http://localhost:8000/api/v1/tasks/workers | jq '.active_workers'
```

#### Execute
```bash
# Start Celery worker with verbose logging
celery -A app.tasks.celery_app worker --loglevel=info &

# Store worker PID for later management
WORKER_PID=$!
echo "Worker PID: $WORKER_PID"
```

#### Validate
```bash
# Verify worker is active
curl -s http://localhost:8000/api/v1/tasks/workers | python -c "
import json, sys
data = json.load(sys.stdin)
print('Active Workers:', data.get('active_workers', 0))
total_processed = sum([sum(worker['total'].values()) for worker in data.get('worker_stats', {}).values() if isinstance(worker, dict) and 'total' in worker])
print('Total Processed:', total_processed)
workers = data.get('workers', {})
print('Worker Names:', list(workers.keys()) if workers else 'None')
"

# Check registered tasks
curl -s http://localhost:8000/api/v1/tasks/registered | python -c "
import json, sys
data = json.load(sys.stdin)
print('Total Tasks:', data.get('task_count', 0))
categories = data.get('categories', {})
for category, tasks in categories.items():
    print(f'{category}: {len(tasks)} tasks')
"
```

**Alternative with jq (if installed):**
```bash
# Verify worker is active
curl -s http://localhost:8000/api/v1/tasks/workers | jq '{
  active_workers: .active_workers,
  total_tasks_processed: ([.worker_stats[] | .total | to_entries[] | .value] | add // 0),
  worker_names: (.active_workers // {} | keys)
}'

# Check registered tasks
curl -s http://localhost:8000/api/v1/tasks/registered | jq '{
  total_tasks: .task_count,
  categories: (.categories | to_entries | map({key, count: (.value | length)}))
}'
```

**Expected Output:**
```json
{
  "active_workers": {
    "celery@hostname": []
  },
  "total_tasks_processed": 25,
  "worker_names": ["celery@hostname"]
}
```

---

### 1.2 Basic Demo Workflow

**Demonstrates:** Task chaining, result persistence, workflow orchestration

#### Setup
```bash
# Ensure Redis is clean for demo
docker compose exec redis redis-cli FLUSHDB
```

#### Execute
```bash
# Start the demo workflow
WORKFLOW_RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/demo/workflow")
echo "$WORKFLOW_RESULT" | jq '.'

# Extract task IDs for monitoring
TASK1=$(echo "$WORKFLOW_RESULT" | jq -r '.tasks[0].task_id')
TASK2=$(echo "$WORKFLOW_RESULT" | jq -r '.tasks[1].task_id')
TASK3=$(echo "$WORKFLOW_RESULT" | jq -r '.tasks[2].task_id')

echo "Task IDs for monitoring:"
echo "Health Check: $TASK1"
echo "Cache Operations: $TASK2"
echo "Data Sync: $TASK3"
```

#### Validate
```bash
# Monitor each task in sequence
echo "=== WORKFLOW MONITORING ==="

echo "📊 Task 1 - Health Check:"
curl -s "http://localhost:8000/api/v1/tasks/result/$TASK1" | python -c "
import json, sys
data = json.load(sys.stdin)
print('Status:', data.get('status', 'unknown'))
print('Ready:', data.get('ready', False))
result = data.get('result', {})
if isinstance(result, dict):
    print('Result Summary:', result.get('status', 'pending'))
else:
    print('Result Summary:', 'pending')
"

sleep 2

echo "📊 Task 2 - Cache Operations:"
curl -s "http://localhost:8000/api/v1/tasks/result/$TASK2" | python -c "
import json, sys
data = json.load(sys.stdin)
print('Status:', data.get('status', 'unknown'))
print('Ready:', data.get('ready', False))
result = data.get('result', {})
if isinstance(result, dict):
    print('Items Cached:', result.get('items_processed', 'pending'))
else:
    print('Items Cached:', 'pending')
"

sleep 2

echo "📊 Task 3 - Data Sync:"
curl -s "http://localhost:8000/api/v1/tasks/result/$TASK3" | python -c "
import json, sys
data = json.load(sys.stdin)
print('Status:', data.get('status', 'unknown'))
print('Ready:', data.get('ready', False))
result = data.get('result', {})
if isinstance(result, dict):
    print('Hostname Created:', result.get('hostname', 'pending'))
else:
    print('Hostname Created:', 'pending')
"
```

**Expected Progression:**
- All tasks start as `PENDING`
- Tasks complete sequentially (health → cache → sync)
- Final status shows `SUCCESS` with results

---

### 1.3 Task Monitoring & Status

**Demonstrates:** Real-time task tracking, result persistence, worker statistics

#### Setup
```bash
# Start multiple concurrent tasks for monitoring demo
TASK_IDS=()
```

#### Execute
```bash
# Launch multiple cache operations
for i in {1..5}; do
  TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/cache/set?key=demo_key_$i&value=demo_value_$i&ttl=300" | jq -r '.task_id')
  TASK_IDS+=($TASK_ID)
  echo "Started task $i: $TASK_ID"
done
```

#### Validate
```bash
# Monitor all tasks simultaneously
echo "=== MULTI-TASK MONITORING ==="
for i in "${!TASK_IDS[@]}"; do
  TASK_ID=${TASK_IDS[$i]}
  echo "Task $((i+1)) (${TASK_ID:0:8}...):"
  curl -s "http://localhost:8000/api/v1/tasks/result/$TASK_ID" | jq '{
    status: .status,
    ready: .ready,
    success: (.result.success // false)
  }'
done

# Check worker statistics
echo "=== WORKER STATISTICS ==="
curl -s http://localhost:8000/api/v1/tasks/workers | jq '{
  active_workers: .active_workers,
  tasks_processed: ([.worker_stats[] | .total | to_entries[] | .value] | add // 0),
  current_load: (.active_workers | to_entries | map(.value | length) | add // 0)
}'
```

---

## 🔄 Level 2: Scalable Operations

*Duration: 10-20 minutes | Complexity: Intermediate*

### 2.1 Batch Processing Showcase

**Demonstrates:** Large-scale operations, progress tracking, error handling

#### Setup
```bash
# Verify database has computers to update
COMPUTER_COUNT=$(curl -s "http://localhost:8000/api/v1/computers/" | jq 'length')
echo "Available computers for batch processing: $COMPUTER_COUNT"

if [ "$COMPUTER_COUNT" -lt 5 ]; then
  echo "⚠️  Creating additional test computers..."
  for i in {1..5}; do
    curl -s -X POST "http://localhost:8000/api/v1/computers/" \
      -H "Content-Type: application/json" \
      -d "{\"hostname\":\"batch-test-$i\",\"status\":\"active\",\"computer_type\":\"laptop\"}" > /dev/null
  done
fi
```

#### Execute
```bash
# Large batch computer update
BATCH_DATA='[
  {"computer_id": 1, "status": "maintenance", "notes": "Batch demo - System update"},
  {"computer_id": 2, "status": "active", "notes": "Batch demo - Health check passed"},
  {"computer_id": 3, "status": "maintenance", "notes": "Batch demo - Hardware upgrade"},
  {"computer_id": 4, "status": "active", "notes": "Batch demo - Software patching"},
  {"computer_id": 5, "status": "maintenance", "notes": "Batch demo - Security scan"}
]'

echo "🚀 Starting batch processing..."
BATCH_RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/crud/batch-update-computers" \
  -H "Content-Type: application/json" \
  -d "$BATCH_DATA")

BATCH_TASK_ID=$(echo "$BATCH_RESULT" | jq -r '.task_id')
echo "Batch Task ID: $BATCH_TASK_ID"
```

#### Validate
```bash
# Monitor batch progress
echo "=== BATCH PROCESSING MONITOR ==="

for i in {1..10}; do
  RESULT=$(curl -s "http://localhost:8000/api/v1/tasks/result/$BATCH_TASK_ID")
  STATUS=$(echo "$RESULT" | jq -r '.status')
  
  echo "Check $i - Status: $STATUS"
  
  if [ "$STATUS" = "SUCCESS" ]; then
    echo "✅ Batch processing completed!"
    echo "$RESULT" | jq '{
      status: .status,
      computers_updated: .result.computers_updated,
      processing_time: .result.processing_time_seconds,
      success_rate: .result.success_rate
    }'
    break
  elif [ "$STATUS" = "FAILURE" ]; then
    echo "❌ Batch processing failed!"
    echo "$RESULT" | jq '.result'
    break
  else
    echo "⏳ Still processing..."
    sleep 2
  fi
done
```

---

### 2.2 Cache Operations Campaign

**Demonstrates:** Redis integration, bulk operations, cache patterns

#### Setup
```bash
# Clear Redis for clean demo
docker compose exec redis redis-cli FLUSHDB

# Check Redis connectivity
REDIS_STATUS=$(docker compose exec redis redis-cli ping)
echo "Redis Status: $REDIS_STATUS"
```

#### Execute
```bash
# Complex cache warm-up campaign
CACHE_PATTERNS='[
  {"pattern": "user_*", "action": "preload", "count": 50},
  {"pattern": "group_*", "action": "refresh", "count": 20},
  {"pattern": "computer_*", "action": "update", "count": 100},
  {"pattern": "incident_*", "action": "cache", "count": 30}
]'

echo "🔄 Starting cache warm-up campaign..."
CACHE_TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/cache/warm-up" \
  -H "Content-Type: application/json" \
  -d "$CACHE_PATTERNS" | jq -r '.task_id')

echo "Cache Task ID: $CACHE_TASK_ID"

# Bulk cache set operation
BULK_DATA='[
  {"key": "demo:metrics:cpu", "value": "75.5", "ttl": 300},
  {"key": "demo:metrics:memory", "value": "82.1", "ttl": 300},
  {"key": "demo:metrics:disk", "value": "45.7", "ttl": 300},
  {"key": "demo:status:system", "value": "healthy", "ttl": 600},
  {"key": "demo:status:database", "value": "connected", "ttl": 600}
]'

BULK_TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/cache/bulk-set" \
  -H "Content-Type: application/json" \
  -d "$BULK_DATA" | jq -r '.task_id')

echo "Bulk Cache Task ID: $BULK_TASK_ID"
```

#### Validate
```bash
# Monitor cache operations
echo "=== CACHE OPERATIONS MONITOR ==="

# Check warm-up progress
echo "📊 Cache Warm-up Status:"
curl -s "http://localhost:8000/api/v1/tasks/result/$CACHE_TASK_ID" | jq '{
  status: .status,
  patterns_processed: (.result.patterns_processed // 0),
  total_operations: (.result.total_operations // 0)
}'

sleep 2

# Check bulk operations
echo "📊 Bulk Cache Status:"
curl -s "http://localhost:8000/api/v1/tasks/result/$BULK_TASK_ID" | jq '{
  status: .status,
  items_cached: (.result.items_processed // 0),
  cache_hits: (.result.cache_hits // 0)
}'

# Verify cache contents
echo "📊 Redis Cache Verification:"
docker compose exec redis redis-cli info keyspace | grep "db0"
docker compose exec redis redis-cli keys "demo:*" | wc -l | xargs echo "Demo keys count:"
```

---

### 2.3 Concurrent Task Management

**Demonstrates:** Parallel execution, load balancing, performance under load

#### Setup
```bash
# Check worker capacity
curl -s http://localhost:8000/api/v1/tasks/workers | jq '{
  workers: .active_workers,
  current_load: (.active_workers | to_entries | map(.value | length) | add // 0)
}'
```

#### Execute
```bash
# Launch multiple concurrent operations
echo "🚀 Starting concurrent task demonstration..."

TASK_IDS=()

# Health checks
for i in {1..3}; do
  TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/cache/health-check" | jq -r '.task_id')
  TASK_IDS+=("health:$TASK_ID")
done

# Cache operations
for i in {1..5}; do
  TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/cache/set?key=concurrent_$i&value=test_value_$i&ttl=300" | jq -r '.task_id')
  TASK_IDS+=("cache:$TASK_ID")
done

# Data operations
TIMESTAMP=$(date +%s)
for i in {1..2}; do
  USER_DATA="{\"username\":\"concurrent_user_${TIMESTAMP}_$i\",\"email\":\"user$i@concurrent${TIMESTAMP}.test\",\"first_name\":\"User\",\"last_name\":\"$i\"}"
  TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/tasks/crud/create-user" \
    -H "Content-Type: application/json" \
    -d "$USER_DATA" | jq -r '.task_id')
  TASK_IDS+=("user:$TASK_ID")
done

echo "Launched ${#TASK_IDS[@]} concurrent tasks"
```

#### Validate
```bash
# Monitor concurrent execution
echo "=== CONCURRENT EXECUTION MONITOR ==="

COMPLETED=0
TOTAL=${#TASK_IDS[@]}

for round in {1..15}; do
  echo "--- Round $round ---"
  CURRENT_COMPLETED=0
  
  for task_info in "${TASK_IDS[@]}"; do
    TYPE=${task_info%:*}
    TASK_ID=${task_info#*:}
    
    STATUS=$(curl -s "http://localhost:8000/api/v1/tasks/result/$TASK_ID" | jq -r '.status // "UNKNOWN"')
    
    if [ "$STATUS" = "SUCCESS" ]; then
      ((CURRENT_COMPLETED++))
    fi
  done
  
  echo "Completed: $CURRENT_COMPLETED/$TOTAL"
  
  if [ $CURRENT_COMPLETED -eq $TOTAL ]; then
    echo "✅ All concurrent tasks completed!"
    break
  fi
  
  # Show worker load
  curl -s http://localhost:8000/api/v1/tasks/workers | jq '{
    active_tasks: (.active_workers | to_entries | map(.value | length) | add // 0)
  }'
  
  sleep 1
done

# Debug incomplete tasks (if any)
if [ $CURRENT_COMPLETED -lt $TOTAL ]; then
  echo "🔍 Debugging incomplete tasks:"
  for task_info in "${TASK_IDS[@]}"; do
    TYPE=${task_info%:*}
    TASK_ID=${task_info#*:}
    STATUS=$(curl -s "http://localhost:8000/api/v1/tasks/result/$TASK_ID" | jq -r '.status // "UNKNOWN"')
    if [ "$STATUS" != "SUCCESS" ]; then
      echo "  ❌ Task $TASK_ID ($TYPE): $STATUS"
    fi
  done
fi

# Final performance summary
echo "=== PERFORMANCE SUMMARY ==="
curl -s http://localhost:8000/api/v1/tasks/workers | jq '{
  workers: .active_workers,
  worker_count: .worker_count,
  status: .status,
  total_processed: ([.worker_stats[] | .total | to_entries[] | .value] | add // 0)
}'
```

---

## 🏢 Level 3: Advanced Orchestration

*Duration: 20-30 minutes | Complexity: Advanced*

### Prerequisites for Level 3

**⚠️ Activation Required:** Advanced orchestration features need to be activated first.

#### Setup
```bash
# Activate orchestration modules (one-time setup)
echo "Activating advanced orchestration features..."

# Backup current celery_app.py
cp app/tasks/celery_app.py app/tasks/celery_app.py.backup

# Update imports to include orchestration
cat > temp_update.py << 'EOF'
import re

with open('app/tasks/celery_app.py', 'r') as f:
    content = f.read()

# Uncomment orchestration imports
content = re.sub(
    r'# from app\.tasks\.orchestration import.*',
    'from app.tasks.orchestration import workflow_tasks, monitoring_tasks, batch_tasks, retry_tasks',
    content
)

with open('app/tasks/celery_app.py', 'w') as f:
    f.write(content)

print("✅ Orchestration modules activated")
EOF

python temp_update.py
rm temp_update.py

# Restart worker to register new tasks
echo "Restarting worker to register new tasks..."
pkill -f "celery.*worker" 2>/dev/null || true
sleep 2
celery -A app.tasks.celery_app worker --loglevel=info &
sleep 5
```

### 3.1 Complex Workflow Patterns

**Demonstrates:** Chains, groups, chords, map-reduce patterns

#### Setup
```bash
# Verify orchestration tasks are registered
ORCHESTRATION_COUNT=$(curl -s http://localhost:8000/api/v1/tasks/registered | jq '.categories.orchestration | length')
echo "Orchestration tasks available: $ORCHESTRATION_COUNT"

if [ "$ORCHESTRATION_COUNT" -eq 0 ]; then
  echo "❌ Orchestration tasks not activated. Please run the Level 3 Prerequisites setup."
  exit 1
fi
```

#### Execute
```bash
# Linear workflow with validation → transformation → enrichment → storage
echo "🔄 Starting linear workflow demonstration..."

WORKFLOW_CONFIG='{
  "input_data": {
    "user_id": 123,
    "data": "complex_workflow_test",
    "metadata": {
      "source": "showcase_demo",
      "timestamp": "'$(date -Iseconds)'"
    }
  },
  "workflow_config": {
    "validation_rules": {
      "required_fields": ["user_id", "data"],
      "data_types": {
        "user_id": "integer",
        "data": "string"
      }
    },
    "transformation_config": {
      "uppercase_fields": ["status"],
      "lowercase_fields": ["data"],
      "trim_fields": ["data"]
    },
    "enrichment_config": {
      "user_lookup": true,
      "department_info": true,
      "permissions": true
    },
    "storage_config": {
      "backend": "database",
      "cache_result": true,
      "ttl": 3600
    }
  }
}'

# Execute via direct task call
WORKFLOW_TASK=$(python -c "
from app.tasks.orchestration.workflow_tasks import linear_workflow
import json

config = json.loads('$WORKFLOW_CONFIG')
result = linear_workflow.delay(config['input_data'], config['workflow_config'])
print(result.id)
")

echo "Linear Workflow Task ID: $WORKFLOW_TASK"

# Parallel workflow demonstration
echo "🔄 Starting parallel workflow demonstration..."

PARALLEL_CONFIG='{
  "tasks": [
    {
      "task_type": "validate_data",
      "data": {"user_id": 1, "field": "email"}
    },
    {
      "task_type": "validate_data",
      "data": {"user_id": 2, "field": "phone"}
    },
    {
      "task_type": "validate_data",
      "data": {"user_id": 3, "field": "address"}
    }
  ],
  "aggregation_config": {
    "collect_results": true,
    "error_handling": "continue_on_failure"
  }
}'

PARALLEL_TASK=$(python -c "
from app.tasks.orchestration.workflow_tasks import parallel_workflow
import json

config = json.loads('$PARALLEL_CONFIG')
result = parallel_workflow.delay(config['tasks'], config['aggregation_config'])
print(result.id)
")

echo "Parallel Workflow Task ID: $PARALLEL_TASK"
```

#### Validate
```bash
# Monitor complex workflows
echo "=== COMPLEX WORKFLOW MONITORING ==="

for i in {1..20}; do
  echo "--- Check $i ---"
  
  echo "📊 Linear Workflow Progress:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$WORKFLOW_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready():
    print(f'Result: {result.result}')
else:
    print('Still processing...')
"
  
  echo "📊 Parallel Workflow Progress:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$PARALLEL_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready():
    print(f'Result: {result.result}')
else:
    print('Still processing...')
"
  
  # Check if both are complete
  BOTH_COMPLETE=$(python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

r1 = AsyncResult('$WORKFLOW_TASK', app=celery_app)
r2 = AsyncResult('$PARALLEL_TASK', app=celery_app)
print('true' if r1.ready() and r2.ready() else 'false')
")
  
  if [ "$BOTH_COMPLETE" = "true" ]; then
    echo "✅ Both workflows completed!"
    break
  fi
  
  sleep 3
done
```

---

### 3.2 Retry & Error Handling

**Demonstrates:** Smart retries, circuit breakers, dead letter queues

#### Setup
```bash
# Prepare for retry demonstration
echo "Setting up retry & error handling demonstration..."

# Check circuit breaker status (if any)
python -c "
try:
    from app.tasks.orchestration.retry_tasks import get_circuit_breaker_status
    print('Circuit breaker functionality available')
except Exception as e:
    print('Circuit breaker setup needed')
"
```

#### Execute
```bash
# Unreliable service call with smart retry
echo "🔄 Testing retry mechanisms with unreliable service..."

RETRY_CONFIG='{
  "service_url": "https://httpstat.us/503",
  "request_data": {"test": "retry_demo"},
  "service_name": "demo_service",
  "retry_config": {
    "max_retries": 3,
    "retry_delay": 2,
    "exponential_backoff": true
  }
}'

RETRY_TASK=$(python -c "
from app.tasks.orchestration.retry_tasks import unreliable_service_call
import json

config = json.loads('$RETRY_CONFIG')
result = unreliable_service_call.delay(
    config['service_url'],
    config['request_data'],
    service_name=config['service_name']
)
print(result.id)
")

echo "Retry Task ID: $RETRY_TASK"

# Database operation with retry
echo "🔄 Testing database operation with retry..."

DB_RETRY_TASK=$(python -c "
from app.tasks.orchestration.retry_tasks import database_operation
result = database_operation.delay(
    'SELECT COUNT(*) FROM users',
    {'simulate_failure': False}
)
print(result.id)
")

echo "Database Retry Task ID: $DB_RETRY_TASK"
```

#### Validate
```bash
# Monitor retry behavior
echo "=== RETRY MECHANISM MONITORING ==="

for i in {1..15}; do
  echo "--- Retry Check $i ---"
  
  echo "📊 Service Call Retry Status:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$RETRY_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready():
    if result.successful():
        print(f'Success: {result.result}')
    else:
        print(f'Failed after retries: {result.result}')
else:
    print('Retrying...')
"
  
  echo "📊 Database Operation Status:"
  python -c "
from celery.result import AsyncResult  
from app.tasks.celery_app import celery_app

result = AsyncResult('$DB_RETRY_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready():
    print(f'Result: {result.result}')
"
  
  sleep 2
  
  # Check if retry task is complete (success or failure)
  RETRY_COMPLETE=$(python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$RETRY_TASK', app=celery_app)
print('true' if result.ready() else 'false')
")
  
  if [ "$RETRY_COMPLETE" = "true" ]; then
    echo "✅ Retry demonstration completed!"
    break
  fi
done

# Analyze retry patterns
echo "📊 Retry Pattern Analysis:"
python -c "
try:
    from app.tasks.orchestration.retry_tasks import analyze_retry_patterns
    result = analyze_retry_patterns.delay(1)  # Last 1 hour
    print(f'Retry Analysis Task ID: {result.id}')
except Exception as e:
    print(f'Retry analysis not available: {e}')
"
```

---

### 3.3 Priority Queue Management

**Demonstrates:** Task prioritization, SLA monitoring, queue routing

#### Setup
```bash
# Check priority queue setup
echo "Setting up priority queue demonstration..."

# Verify priority tasks are available
python -c "
try:
    from app.tasks.orchestration.priority_tasks import submit_priority_task
    print('✅ Priority queue functionality available')
except Exception as e:
    print(f'❌ Priority queue setup needed: {e}')
"
```

#### Execute
```bash
# High-priority task submission
echo "🚀 Submitting high-priority tasks..."

HIGH_PRIORITY_TASK=$(python -c "
from app.tasks.orchestration.priority_tasks import submit_priority_task
result = submit_priority_task.delay(
    task_name='priority.high_priority_data_processing',
    task_args=[{'urgent_data': 'critical_system_alert'}],
    task_kwargs={'config': {'processing_time': 0.5}},
    config={
        'priority': 90,
        'queue_type': 'interactive',
        'sla_seconds': 5.0,
        'timeout_seconds': 10.0
    }
)
print(result.id)
")

echo "High Priority Task ID: $HIGH_PRIORITY_TASK"

# Low-priority background task
LOW_PRIORITY_TASK=$(python -c "
from app.tasks.orchestration.priority_tasks import submit_priority_task
result = submit_priority_task.delay(
    task_name='priority.background_batch_processing',
    task_args=[{'batch_data': 'large_dataset_processing'}],
    task_kwargs={'config': {'processing_time': 2.0}},
    config={
        'priority': 10,
        'queue_type': 'background',
        'sla_seconds': 30.0,
        'timeout_seconds': 60.0
    }
)
print(result.id)
")

echo "Low Priority Task ID: $LOW_PRIORITY_TASK"

# Medium-priority task for comparison
MEDIUM_PRIORITY_TASK=$(python -c "
from app.tasks.orchestration.priority_tasks import submit_priority_task
result = submit_priority_task.delay(
    task_name='priority.bulk_low_priority_processing',
    task_args=[{'bulk_data': 'routine_data_sync'}],
    task_kwargs={'config': {'processing_time': 1.0}},
    config={
        'priority': 50,
        'queue_type': 'standard',
        'sla_seconds': 15.0,
        'timeout_seconds': 30.0
    }
)
print(result.id)
")

echo "Medium Priority Task ID: $MEDIUM_PRIORITY_TASK"
```

#### Validate
```bash
# Monitor priority execution order
echo "=== PRIORITY QUEUE MONITORING ==="

# Track execution order and timing
START_TIME=$(date +%s)

for i in {1..20}; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  echo "--- Priority Check $i (${ELAPSED}s elapsed) ---"
  
  # Check high priority
  HIGH_STATUS=$(python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app
result = AsyncResult('$HIGH_PRIORITY_TASK', app=celery_app)
print(result.status)
")
  
  # Check medium priority
  MEDIUM_STATUS=$(python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app
result = AsyncResult('$MEDIUM_PRIORITY_TASK', app=celery_app)
print(result.status)
")
  
  # Check low priority
  LOW_STATUS=$(python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app
result = AsyncResult('$LOW_PRIORITY_TASK', app=celery_app)
print(result.status)
")
  
  echo "High Priority (SLA: 5s):   $HIGH_STATUS"
  echo "Medium Priority (SLA: 15s): $MEDIUM_STATUS"
  echo "Low Priority (SLA: 30s):    $LOW_STATUS"
  
  # Check for SLA violations
  if [ $ELAPSED -gt 5 ] && [ "$HIGH_STATUS" != "SUCCESS" ]; then
    echo "⚠️  HIGH PRIORITY SLA VIOLATION (>5s)"
  fi
  
  if [ $ELAPSED -gt 15 ] && [ "$MEDIUM_STATUS" != "SUCCESS" ]; then
    echo "⚠️  MEDIUM PRIORITY SLA VIOLATION (>15s)"
  fi
  
  # Check if all complete
  if [ "$HIGH_STATUS" = "SUCCESS" ] && [ "$MEDIUM_STATUS" = "SUCCESS" ] && [ "$LOW_STATUS" = "SUCCESS" ]; then
    echo "✅ All priority tasks completed!"
    break
  fi
  
  sleep 1
done

# Priority performance analysis
echo "📊 Priority Performance Analysis:"
python -c "
try:
    from app.tasks.orchestration.priority_tasks import analyze_priority_performance
    result = analyze_priority_performance.delay()
    print(f'Priority Analysis Task ID: {result.id}')
except Exception as e:
    print(f'Priority analysis not available: {e}')
"
```

---

## 🏭 Level 4: Enterprise Workflows

*Duration: 30+ minutes | Complexity: Expert*

### Prerequisites for Level 4

#### Setup
```bash
# Activate enterprise modules
echo "Activating enterprise workflow features..."

# Update imports to include enterprise modules
cat > temp_enterprise_update.py << 'EOF'
import re

with open('app/tasks/celery_app.py', 'r') as f:
    content = f.read()

# Uncomment enterprise imports
content = re.sub(
    r'# from app\.tasks\.enterprise import.*',
    'from app.tasks.enterprise import security_workflows, compliance_tasks, user_onboarding',
    content
)

with open('app/tasks/celery_app.py', 'w') as f:
    f.write(content)

print("✅ Enterprise modules activated")
EOF

python temp_enterprise_update.py
rm temp_enterprise_update.py

# Restart worker for enterprise tasks
echo "Restarting worker for enterprise task registration..."
pkill -f "celery.*worker" 2>/dev/null || true
sleep 2
celery -A app.tasks.celery_app worker --loglevel=info &
sleep 5

# Verify enterprise tasks are registered
ENTERPRISE_COUNT=$(curl -s http://localhost:8000/api/v1/tasks/registered | jq '.categories.enterprise | length')
echo "Enterprise tasks available: $ENTERPRISE_COUNT"
```

### 4.1 Continuous Monitoring System

**Demonstrates:** Self-scheduling tasks, system health monitoring, automated alerting

#### Setup
```bash
# Configure monitoring parameters
MONITORING_CONFIG='{
  "sources": [
    "network_traffic",
    "system_logs", 
    "application_logs",
    "user_activity",
    "endpoint_detection"
  ],
  "cycle_interval_seconds": 60,
  "alert_rules": [
    {
      "name": "high_cpu",
      "metric_path": "system.cpu.percent",
      "operator": "gt",
      "threshold": 80,
      "severity": "warning"
    },
    {
      "name": "high_memory",
      "metric_path": "system.memory.percent", 
      "operator": "gt",
      "threshold": 90,
      "severity": "critical"
    }
  ]
}'

echo "Starting continuous monitoring system..."
```

#### Execute
```bash
# Start continuous security monitoring (self-scheduling)
SECURITY_MONITOR_TASK=$(python -c "
from app.tasks.enterprise.security_workflows import continuous_security_monitoring
import json

config = json.loads('$MONITORING_CONFIG')
result = continuous_security_monitoring.delay(config)
print(result.id)
")

echo "Continuous Security Monitoring Task ID: $SECURITY_MONITOR_TASK"

# Start system health monitoring cycle
HEALTH_MONITOR_TASK=$(python -c "
from app.tasks.orchestration.monitoring_tasks import full_monitoring_cycle
import json

config = json.loads('$MONITORING_CONFIG')
result = full_monitoring_cycle.delay(config)
print(result.id)
")

echo "Health Monitoring Cycle Task ID: $HEALTH_MONITOR_TASK"

echo "🔄 Monitoring systems are now running continuously..."
echo "📊 These tasks will self-schedule and run every 60 seconds"
```

#### Validate
```bash
# Extended monitoring validation (run for several cycles)
echo "=== CONTINUOUS MONITORING VALIDATION ==="
echo "⏰ Monitoring for 5 minutes to show continuous operation..."

START_TIME=$(date +%s)
MONITORING_CYCLES=0

for i in {1..20}; do  # 5 minutes of monitoring
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  echo "--- Monitoring Check $i (${ELAPSED}s elapsed) ---"
  
  # Check security monitoring status
  echo "🔒 Security Monitoring:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$SECURITY_MONITOR_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready() and result.successful():
    r = result.result
    print(f'Sources monitored: {r.get(\"sources_monitored\", 0)}')
    print(f'Next cycle: {r.get(\"next_cycle_scheduled\", \"unknown\")}')
"
  
  # Check health monitoring
  echo "🏥 Health Monitoring:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$HEALTH_MONITOR_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready() and result.successful():
    r = result.result
    print(f'Overall status: {r.get(\"overall_status\", \"unknown\")}')
    print(f'Cycle duration: {r.get(\"cycle_duration_seconds\", 0):.1f}s')
"
  
  # Check for new monitoring cycles (self-scheduled tasks)
  if [ $((ELAPSED % 60)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
    ((MONITORING_CYCLES++))
    echo "🔄 Monitoring cycle $MONITORING_CYCLES completed"
  fi
  
  # Check worker load
  ACTIVE_TASKS=$(curl -s http://localhost:8000/api/v1/tasks/workers | jq '.active_workers | to_entries | map(.value | length) | add // 0')
  echo "Active tasks in queue: $ACTIVE_TASKS"
  
  if [ $ELAPSED -ge 300 ]; then  # 5 minutes
    echo "✅ Continuous monitoring demonstration completed!"
    echo "📊 Monitoring cycles observed: $MONITORING_CYCLES"
    break
  fi
  
  sleep 15
done
```

---

### 4.2 Security & Compliance Automation

**Demonstrates:** Multi-framework compliance, automated assessments, reporting

#### Setup
```bash
# Configure comprehensive compliance assessment
COMPLIANCE_CONFIG='{
  "frameworks": ["SOX", "PCI_DSS", "GDPR", "HIPAA"],
  "scope": "full",
  "assessment_depth": "comprehensive",
  "generate_report": true,
  "notify_stakeholders": true,
  "parallel_execution": true
}'

echo "Setting up comprehensive compliance assessment..."
```

#### Execute
```bash
# Start comprehensive compliance assessment
COMPLIANCE_TASK=$(python -c "
from app.tasks.enterprise.compliance_tasks import run_comprehensive_assessment
import json

config = json.loads('$COMPLIANCE_CONFIG')
result = run_comprehensive_assessment.delay(config)
print(result.id)
")

echo "Comprehensive Compliance Assessment Task ID: $COMPLIANCE_TASK"

# Individual framework assessment for comparison
SOX_ASSESSMENT_TASK=$(python -c "
from app.tasks.enterprise.compliance_tasks import assess_framework_compliance
result = assess_framework_compliance.delay('SOX', {'scope': 'financial_controls'})
print(result.id)
")

echo "SOX Framework Assessment Task ID: $SOX_ASSESSMENT_TASK"

echo "🏢 Enterprise compliance assessment in progress..."
echo "📋 This includes parallel assessment of multiple frameworks"
```

#### Validate
```bash
# Monitor compliance assessment progress
echo "=== COMPLIANCE ASSESSMENT MONITORING ==="

for i in {1..30}; do  # Extended monitoring for complex assessment
  echo "--- Compliance Check $i ---"
  
  # Check comprehensive assessment
  echo "📊 Comprehensive Assessment:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$COMPLIANCE_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready():
    if result.successful():
        r = result.result
        print(f'Frameworks assessed: {len(r.get(\"frameworks_assessed\", []))}')
        print(f'Assessment scope: {r.get(\"assessment_scope\", \"unknown\")}')
        print(f'Assessment ID: {r.get(\"assessment_id\", \"unknown\")}')
    else:
        print(f'Assessment failed: {result.result}')
else:
    print('Assessment in progress...')
"
  
  # Check SOX individual assessment
  echo "📊 SOX Framework Assessment:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$SOX_ASSESSMENT_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready() and result.successful():
    r = result.result
    print(f'Framework: {r.get(\"framework\", \"unknown\")}')
    print(f'Compliance score: {r.get(\"compliance_score\", \"unknown\")}')
"
  
  # Check if comprehensive assessment is complete
  ASSESSMENT_COMPLETE=$(python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$COMPLIANCE_TASK', app=celery_app)
print('true' if result.ready() else 'false')
")
  
  if [ "$ASSESSMENT_COMPLETE" = "true" ]; then
    echo "✅ Compliance assessment completed!"
    
    # Check for follow-up tasks (report generation, notifications)
    echo "📊 Checking for follow-up tasks..."
    python -c "
try:
    from app.tasks.enterprise.compliance_tasks import generate_compliance_report
    print('Report generation task available')
except Exception as e:
    print('Report generation: not available')
"
    break
  fi
  
  sleep 10
done
```

---

### 4.3 User Onboarding Orchestration

**Demonstrates:** Multi-stage workflows, dependency management, lifecycle automation

#### Setup
```bash
# Configure complete employee onboarding
ONBOARDING_CONFIG='{
  "employee_data": {
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah.johnson@company.com",
    "department": "Engineering",
    "position": "Senior Software Engineer",
    "manager_id": 101,
    "start_date": "'$(date -d "+7 days" -I)'",
    "employee_type": "full_time",
    "employee_id": "EMP'$(date +%Y%m%d%H%M)'"
  },
  "onboarding_config": {
    "create_accounts": {
      "active_directory": true,
      "email": true,
      "slack": true,
      "jira": true,
      "confluence": true
    },
    "provision_equipment": {
      "laptop": "macbook_pro_16",
      "monitor": "external_4k",
      "accessories": ["keyboard", "mouse", "headset"]
    },
    "training_modules": [
      "security_awareness",
      "company_policies",
      "engineering_onboarding",
      "git_workflows"
    ],
    "schedule_meetings": {
      "hr_orientation": true,
      "manager_1on1": true,
      "team_introduction": true
    },
    "workflow_stages": [
      "pre_start_preparation",
      "day_one_orientation", 
      "first_week_integration",
      "thirty_day_review"
    ]
  }
}'

echo "Setting up comprehensive user onboarding workflow..."
```

#### Execute
```bash
# Start comprehensive onboarding workflow
ONBOARDING_TASK=$(python -c "
from app.tasks.enterprise.user_onboarding import orchestrate_complete_onboarding
import json

config = json.loads('$ONBOARDING_CONFIG')
result = orchestrate_complete_onboarding.delay(
    config['employee_data'],
    config['onboarding_config']
)
print(result.id)
")

echo "Complete Onboarding Workflow Task ID: $ONBOARDING_TASK"

# Start pre-start preparation (can run in parallel)
PRESTART_TASK=$(python -c "
from app.tasks.enterprise.user_onboarding import execute_pre_start_onboarding
import json

config = json.loads('$ONBOARDING_CONFIG')
result = execute_pre_start_onboarding.delay(
    config['employee_data'],
    config['onboarding_config']
)
print(result.id)
")

echo "Pre-start Preparation Task ID: $PRESTART_TASK"

echo "🏢 Enterprise onboarding workflow initiated..."
echo "👤 Multi-stage workflow with dependency management"
```

#### Validate
```bash
# Extended onboarding workflow monitoring
echo "=== ONBOARDING WORKFLOW MONITORING ==="

for i in {1..40}; do  # Extended monitoring for multi-stage workflow
  echo "--- Onboarding Check $i ---"
  
  # Check main onboarding workflow
  echo "📊 Complete Onboarding Workflow:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$ONBOARDING_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready():
    if result.successful():
        r = result.result
        print(f'Employee ID: {r.get(\"employee_id\", \"unknown\")}')
        print(f'Workflow stages: {len(r.get(\"workflow_stages\", []))}')
        print(f'Completion status: {r.get(\"completion_status\", \"unknown\")}')
    else:
        print(f'Workflow failed: {result.result}')
else:
    print('Workflow in progress...')
"
  
  # Check pre-start preparation
  echo "📊 Pre-start Preparation:"
  python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$PRESTART_TASK', app=celery_app)
print(f'Status: {result.status}')
if result.ready() and result.successful():
    r = result.result
    print(f'Pre-start tasks: {r.get(\"tasks_completed\", 0)}')
    print(f'Equipment status: {r.get(\"equipment_status\", \"unknown\")}')
"
  
  # Check worker queue status
  QUEUE_STATUS=$(curl -s http://localhost:8000/api/v1/tasks/workers | jq '{
    active_workers: .active_workers,
    active_tasks: (.active_workers | to_entries | map(.value | length) | add // 0)
  }')
  echo "📊 Worker Status: $QUEUE_STATUS"
  
  # Check if onboarding workflow is complete
  ONBOARDING_COMPLETE=$(python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$ONBOARDING_TASK', app=celery_app)
print('true' if result.ready() else 'false')
")
  
  if [ "$ONBOARDING_COMPLETE" = "true" ]; then
    echo "✅ Onboarding workflow completed!"
    
    # Show final workflow summary
    echo "📊 Final Onboarding Summary:"
    python -c "
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

result = AsyncResult('$ONBOARDING_TASK', app=celery_app)
if result.successful():
    import json
    print(json.dumps(result.result, indent=2))
"
    break
  fi
  
  sleep 8
done
```

---

## 📊 Monitoring & Analytics

### Real-time Dashboards

#### System Health Dashboard
```bash
# Continuous system health monitoring
watch -n 5 'echo "=== SYSTEM HEALTH DASHBOARD ==="; 
curl -s http://localhost:8000/api/v1/monitoring/health | jq "{
  status: .status,
  database: .database,
  redis: .redis,
  celery_workers: .celery_workers,
  system_load: .system_load
}";
echo;
echo "=== WORKER STATUS ===";
curl -s http://localhost:8000/api/v1/tasks/workers | jq "{
  active_workers: .active_workers,
  total_processed: ([.worker_stats[] | .total | to_entries[] | .value] | add // 0),
  active_tasks: (.active_workers | to_entries | map(.value | length) | add // 0)
}"'
```

#### Task Performance Dashboard
```bash
# Task performance monitoring
watch -n 3 'echo "=== TASK PERFORMANCE ===";
curl -s http://localhost:8000/api/v1/monitoring/metrics/performance | jq "{
  avg_response_time: .avg_response_time_ms,
  tasks_per_minute: .tasks_per_minute,
  success_rate: .success_rate_percent,
  error_rate: .error_rate_percent
}";
echo;
echo "=== QUEUE STATUS ===";
celery -A app.tasks.celery_app inspect active | head -10'
```

### Performance Metrics

#### Celery Performance Analysis
```bash
# Comprehensive Celery performance metrics
echo "=== CELERY PERFORMANCE ANALYSIS ==="

# Worker statistics
echo "📊 Worker Statistics:"
celery -A app.tasks.celery_app inspect stats

# Active tasks
echo "📊 Active Tasks:"
celery -A app.tasks.celery_app inspect active

# Reserved tasks
echo "📊 Reserved Tasks:"
celery -A app.tasks.celery_app inspect reserved

# Scheduled tasks
echo "📊 Scheduled Tasks:"
celery -A app.tasks.celery_app inspect scheduled
```

#### Redis Performance Monitoring
```bash
# Redis performance metrics
echo "=== REDIS PERFORMANCE ==="

# Redis info
echo "📊 Redis Server Info:"
docker compose exec redis redis-cli info server | grep -E "(redis_version|uptime|connected_clients)"

# Memory usage
echo "📊 Redis Memory Usage:"
docker compose exec redis redis-cli info memory | grep -E "(used_memory|used_memory_peak)"

# Key statistics
echo "📊 Redis Key Statistics:"
docker compose exec redis redis-cli info keyspace

# Current keys
echo "📊 Current Cache Keys:"
docker compose exec redis redis-cli keys "*" | head -10
```

### Extended Monitoring Setup

#### Flower Monitoring (Optional)
```bash
# Start Flower for web-based monitoring
echo "Starting Flower monitoring interface..."
celery -A app.tasks.celery_app flower --port=5555 &

echo "🌸 Flower monitoring available at: http://localhost:5555"
echo "📊 Features available:"
echo "  - Real-time task monitoring"
echo "  - Worker management"
echo "  - Task history and statistics"
echo "  - Broker monitoring"
```

#### Log Monitoring
```bash
# Comprehensive log monitoring setup
echo "=== LOG MONITORING SETUP ==="

# Worker logs
echo "📊 Worker Logs (last 20 lines):"
tail -20 /var/log/celery/worker.log 2>/dev/null || echo "Worker logs not found at default location"

# Application logs
echo "📊 Application Logs:"
tail -20 /var/log/fastapi/app.log 2>/dev/null || echo "App logs not found at default location"

# Real-time log monitoring command
echo "💡 For real-time log monitoring, use:"
echo "tail -f /var/log/celery/worker.log"
echo "tail -f /var/log/fastapi/app.log"
```

#### Custom Monitoring Script
```bash
# Create comprehensive monitoring script
cat > monitor_celery_showcase.sh << 'EOF'
#!/bin/bash

echo "🔍 CELERY SHOWCASE MONITORING"
echo "=============================="

while true; do
    clear
    echo "🔍 CELERY SHOWCASE MONITORING - $(date)"
    echo "=============================="
    
    # System health
    echo "🏥 System Health:"
    curl -s http://localhost:8000/api/v1/monitoring/health | jq -r '
        "Status: \(.status // "unknown")",
        "Database: \(.database // "unknown")",
        "Redis: \(.redis // "unknown")",
        "Workers: \(.celery_workers // "unknown")"
    '
    echo
    
    # Worker status
    echo "⚙️  Worker Status:"
    curl -s http://localhost:8000/api/v1/tasks/workers | jq -r '
        "Active Workers: \(.worker_count // 0)",
        "Total Processed: \(([.worker_stats[] | .total | to_entries[] | .value] | add) // 0)",
        "Active Tasks: \((.active_workers // {} | to_entries | map(.value | length) | add) // 0)"
    '
    echo
    
    # Recent tasks
    echo "📋 Recent Task Activity:"
    celery -A app.tasks.celery_app inspect active | head -5
    echo
    
    # Redis stats
    echo "🗄️  Redis Status:"
    docker compose exec redis redis-cli info keyspace 2>/dev/null | head -3 || echo "Redis unavailable"
    echo
    
    echo "Press Ctrl+C to stop monitoring"
    sleep 10
done
EOF

chmod +x monitor_celery_showcase.sh

echo "✅ Monitoring script created: ./monitor_celery_showcase.sh"
echo "🚀 Run with: ./monitor_celery_showcase.sh"
```

---

## 🎯 Quick Reference Commands

### Start Complete Showcase Environment
```bash
# Full environment startup
docker compose up -d redis
celery -A app.tasks.celery_app worker --loglevel=info &
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
celery -A app.tasks.celery_app flower --port=5555 &  # Optional
```

### Activate All Advanced Features
```bash
# Activate orchestration and enterprise features
sed -i 's/# from app\.tasks\.orchestration/from app.tasks.orchestration/' app/tasks/celery_app.py
sed -i 's/# from app\.tasks\.enterprise/from app.tasks.enterprise/' app/tasks/celery_app.py

# Restart worker
pkill -f "celery.*worker"
celery -A app.tasks.celery_app worker --loglevel=info &
```

### Essential Monitoring Commands
```bash
# Worker status
curl -s http://localhost:8000/api/v1/tasks/workers | jq '.'

# System health
curl -s http://localhost:8000/api/v1/monitoring/health | jq '.'

# Task registry
curl -s http://localhost:8000/api/v1/tasks/registered | jq '.task_count'

# Active tasks
celery -A app.tasks.celery_app inspect active

# Redis status
docker compose exec redis redis-cli ping
```

---

## 📈 Expected Performance Benchmarks

| Complexity Level | Task Count | Duration | Success Rate | Resource Usage |
|------------------|------------|----------|--------------|----------------|
| **Level 1** | 3-10 tasks | 5-10 minutes | >95% | Low |
| **Level 2** | 10-50 tasks | 10-20 minutes | >90% | Medium |
| **Level 3** | 20-100+ tasks | 20-30 minutes | >85% | Medium-High |
| **Level 4** | 50-200+ tasks | 30+ minutes | >80% | High |

## 🏆 Showcase Success Criteria

✅ **Foundation (Level 1):** Worker lifecycle, basic workflows, task monitoring  
✅ **Scalability (Level 2):** Batch processing, concurrent operations, cache management  
✅ **Advanced (Level 3):** Complex workflows, retry patterns, priority queues  
✅ **Enterprise (Level 4):** Continuous monitoring, compliance automation, multi-stage workflows  

---

**🎉 This showcase demonstrates a production-ready Celery implementation with enterprise-grade capabilities!**
