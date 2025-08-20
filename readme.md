# Main Objective
Showcase the functionality and capability of a Celery implementation to complement an existing FastAPI project which already leverages Redis, SQLAlchemy, Pydantic and Postgres/SQLite (locally). Build an IT Asset & Incident Management middleware that demonstrates advanced Celery capabilities within enterprise development patterns.

# General Context
This is a server side concept/MVP that exists within a broader ecosystem, which includes an existing client side app and database. The primary purpose is middleware, handling API requests and data reconciliation for the client side app. This includes handling API calls, database queries and related efforts using REST API structures.

## Ecosystem Context
It can be assumed this full stack approach and surrounding infrastructure/resources exist within a large scale enterprise domain. There are no public resources or endpoints in scope.

**Domain Focus**: IT Asset & Incident Management
- Data structures involve user, group and computer information, as well as event and incident data
- Target audience: technical users, operations support and system administrators
- Enterprise-style schemas based on Active Directory patterns

## Technical Decisions
- **API Design**: REST endpoints only (no GraphQL for simplicity)
- **Database**: SQLite for local development with enterprise-style schemas
- **Mock Strategy**: Unified factory pattern for external system simulation
- **Project Structure**: Feature-based modules optimized for Celery showcase
- **Task Complexity**: Mixed approach (quick demos + realistic scenarios) 


# Required Packages
- FastAPI
- Pydantic
- Sqlalchmey
- Redis
- Celery
- [suggested] flower
- [suggested] celery[redis]
- [suggested] faker

# Conditions
- Fully operable in local runtime
- Clear separation of duties
- Domain-driven design
- Block level and inline comments optimized for llm/agent use
- No unit, functional or end to end tests required
- No authentication required
- No CI/CD, deployment configuration required

# Supported Workflows

## Core Cache & Database Workflows
1. **Full-scope, all resources; return cache and fresh first, fallback**
Inbound API request received, steps:
- Redis checked: if found and fresh, data is returned, else...
- Database checked: if found and fresh, Redis is updated, data is returned, else...
- Refresh task: reconcile and update Database, Redis

2. **Redis + Database integration**
Examples: 
- Long-running query/report (updated on schedule)
- Slow API responses
- A group is accessed; cache updates to fetch database/api ahead of time
- A user authenticates; cache updates to fetch team/group information ahead of time

3. **Direct to celery: Batch, scheduled tasks**

## Advanced Celery Orchestration Workflows
4. **Chain/Group Tasks**: Sequential and parallel task execution with dependency management
- Task chains: Step A → Step B → Step C execution flow
- Task groups: Parallel execution with result aggregation

5. **Periodic Tasks (Celery Beat)**: Scheduled background operations
- Cron-style scheduling for recurring operations
- Dynamic scheduling based on system state

6. **Task Retries & Error Handling**: Robust failure management
- Exponential backoff strategies
- Dead letter queues for failed tasks
- Graceful degradation patterns

7. **Canvas Workflows**: Complex task composition patterns
- Chord operations: Parallel tasks → single callback
- Map-reduce style operations
- Nested workflow orchestration

8. **Priority Queues & Task Routing**: Advanced task management
- Multiple queue priorities
- Task routing to specific workers
- Dynamic load balancing

9. **Task Results Backend**: Progress tracking and result persistence
- Long-running task progress monitoring
- Result caching and retrieval
- Task status API endpoints

## FastAPI Integration Workflows
10. **Async endpoint integration**: Native FastAPI async with Celery task spawning

11. **Streaming responses**: Real-time data delivery via SSE/WebSocket integration

12. **Monitoring, management of redis and celery states**: Health checks and system observability

Avoid use of webpack, polling unless required

# Data Models & Domain Structure

## Core Entities
- **Users**: AD-style attributes (username, email, groups, department, status)
- **Groups**: Enterprise group structure (name, permissions, members, hierarchy)  
- **Computers**: Asset tracking (hostname, IP, OS, status, owner, last_seen)
- **Events**: System events (timestamp, source, type, severity, metadata)
- **Incidents**: IT incidents (ticket_id, status, assignee, priority, description)

## Mock External Systems
- **Unified factory pattern** for external integrations
- **AD/LDAP simulation** for user/group synchronization
- **Monitoring agents** for computer health data collection
- **Ticketing system** for incident management workflows
- **Database-driven mocks** leveraging SQLAlchemy and faker

# Implementation Approach

## Project Structure
Feature-based modules optimized for Celery showcase:
- Clean separation between API layer, business logic, and task orchestration
- Easy-to-follow Celery configuration and adoption patterns
- Domain-driven design principles with LLM-optimized documentation

### Directory Structure
```
/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py             # Application configuration
│   │   └── celery_config.py        # Celery configuration and setup
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py             # SQLAlchemy database setup
│   │   ├── redis.py                # Redis connection management
│   │   └── dependencies.py         # FastAPI dependency injection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── users.py                # User/Group SQLAlchemy models
│   │   ├── computers.py            # Computer asset models
│   │   └── incidents.py            # Event/Incident models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── users.py                # User/Group Pydantic schemas
│   │   ├── computers.py            # Computer Pydantic schemas
│   │   └── incidents.py            # Event/Incident Pydantic schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── users.py            # User CRUD REST endpoints
│   │   │   ├── computers.py        # Computer CRUD REST endpoints
│   │   │   ├── incidents.py        # Incident CRUD REST endpoints
│   │   │   ├── tasks.py            # Task management/status endpoints
│   │   │   └── monitoring.py       # Health checks/system observability
│   │   └── dependencies.py         # API-specific dependencies
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Celery application instance
│   │   ├── basic/
│   │   │   ├── __init__.py
│   │   │   ├── cache_tasks.py      # Redis cache operations
│   │   │   └── crud_tasks.py       # Basic database operations
│   │   ├── orchestration/
│   │   │   ├── __init__.py
│   │   │   ├── chains.py           # Chain/Group task patterns
│   │   │   ├── periodic.py         # Celery Beat scheduled tasks
│   │   │   ├── canvas.py           # Chord/Canvas workflow patterns
│   │   │   └── retries.py          # Retry/error handling patterns
│   │   └── enterprise/
│   │       ├── __init__.py
│   │       ├── asset_sync.py       # Computer asset synchronization
│   │       ├── incident_workflows.py # Incident processing workflows
│   │       └── reporting.py        # Report generation tasks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cache_service.py        # Redis operations service layer
│   │   ├── database_service.py     # Database operations service layer
│   │   └── external_mocks.py       # Mock external system integrations
│   └── utils/
│       ├── __init__.py
│       ├── logging.py              # Logging configuration
│       └── helpers.py              # Utility functions and helpers
├── scripts/
│   ├── setup_db.py                 # Database initialization script
│   ├── seed_data.py                # Mock data generation with faker
│   └── run_workers.py              # Celery worker startup script
├── requirements.txt                # Python package dependencies
├── .env.example                    # Environment variables template
└── README.md                       # Project documentation
```

## API Endpoints
- **CRUD operations** for core entities (Users, Groups, Computers, Events, Incidents)
- **Task management** endpoints (status, results, monitoring)
- **Real-time streaming** via Server-Sent Events for live updates
- **Health checks** and system observability

## Task Complexity Strategy
- **Quick demos (1-5 seconds)**: Basic CRUD, cache operations, simple chains
- **Realistic scenarios (10-30 seconds)**: Report generation, system scanning, multi-step workflows
- **Progressive complexity** demonstrating Celery's full orchestration capabilities

# Key Deliverables

1. **Fully operational local environment** with all services integrated
2. **Comprehensive Celery patterns** from basic to advanced orchestration
3. **Real-world enterprise scenarios** that technical teams can relate to
4. **Clear documentation** optimized for LLM understanding and human learning
5. **Extensible architecture** for easy feature addition and experimentation

# Development Guidelines

- **Focus**: Celery orchestration patterns and integration techniques
- **Scope**: IT Asset & Incident Management middleware showcase
- **Complexity**: Balance between demonstration value and maintainability
- **Extensibility**: Design for easy addition of new Celery scenarios 