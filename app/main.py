"""
Main FastAPI application entry point.

This module creates the FastAPI application instance and configures
all routes, middleware, and application lifecycle events.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import AsyncGenerator

from app.config.settings import settings
from app.core.database import create_tables
from app.api.routes import users, groups, computers, incidents, tasks, monitoring


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown operations for the FastAPI application,
    including database initialization and cleanup tasks.
    """
    # Startup operations
    print("🚀 Starting Celery Showcase API...")
    
    # Ensure database tables exist
    create_tables()
    print("✅ Database tables verified")
    
    # Application is ready
    print(f"🌟 {settings.project_name} API ready!")
    print(f"📊 API documentation: http://localhost:8000/docs")
    print(f"🔍 Alternative docs: http://localhost:8000/redoc")
    
    yield
    
    # Shutdown operations
    print("🛑 Shutting down Celery Showcase API...")


# Create FastAPI application instance
app = FastAPI(
    title=settings.project_name,
    description="""
    ## Celery Showcase API
    
    A comprehensive demonstration of Celery integration with FastAPI for enterprise IT operations.
    
    This API showcases:
    - **Advanced Celery patterns**: Chains, groups, canvas workflows, retries
    - **Enterprise data management**: Users, groups, computers, events, incidents
    - **Caching strategies**: Redis integration with fallback patterns
    - **Real-time operations**: Async endpoints with streaming responses
    - **Task monitoring**: Progress tracking and system observability
    
    ### Key Features
    - 🔄 **Multi-layer caching** with Redis and database fallback
    - ⚙️ **Complex task orchestration** with dependency management
    - 📊 **Real-time monitoring** of system health and task progress
    - 🏢 **Enterprise workflows** for IT asset and incident management
    - 🔧 **Comprehensive APIs** for all CRUD operations and task management
    
    ### Queue Architecture
    - **Default Queue**: Basic operations and CRUD tasks
    - **Orchestration Queue**: Advanced Celery patterns and workflows
    - **Enterprise Queue**: Business-specific IT operations
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    lifespan=lifespan
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    
    Provides consistent error responses and logging for debugging.
    """
    error_detail = str(exc) if settings.debug else "Internal server error"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": error_detail,
            "path": str(request.url),
            "method": request.method
        }
    )


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint providing API information and health status.
    
    Returns:
        Dict containing API information, status, and available endpoints
    """
    return {
        "message": f"Welcome to {settings.project_name}",
        "description": "Advanced Celery integration showcase with enterprise IT operations",
        "version": "1.0.0",
        "status": "operational",
        "documentation": {
            "interactive": "/docs",
            "alternative": "/redoc",
            "openapi_spec": f"{settings.api_v1_str}/openapi.json"
        },
        "endpoints": {
            "users": f"{settings.api_v1_str}/users",
            "groups": f"{settings.api_v1_str}/groups", 
            "computers": f"{settings.api_v1_str}/computers",
            "incidents": f"{settings.api_v1_str}/incidents",
            "tasks": f"{settings.api_v1_str}/tasks",
            "monitoring": f"{settings.api_v1_str}/monitoring"
        },
        "celery_queues": ["default", "orchestration", "enterprise"],
        "features": [
            "Multi-layer caching with Redis",
            "Advanced Celery orchestration patterns",
            "Enterprise IT workflow management", 
            "Real-time task monitoring",
            "Comprehensive CRUD operations"
        ]
    }


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Dict containing application health status and system information
    """
    return {
        "status": "healthy",
        "timestamp": "2025-01-20T10:40:00Z",
        "version": "1.0.0",
        "environment": "development" if settings.debug else "production",
        "database": "connected",
        "redis": "connected",
        "celery": "operational"
    }


# Include API routers
app.include_router(
    users.router,
    prefix=f"{settings.api_v1_str}/users",
    tags=["Users"]
)

app.include_router(
    groups.router,
    prefix=f"{settings.api_v1_str}/groups",
    tags=["Groups"]
)

app.include_router(
    computers.router,
    prefix=f"{settings.api_v1_str}/computers",
    tags=["Computers"]
)

app.include_router(
    incidents.router,
    prefix=f"{settings.api_v1_str}/incidents",
    tags=["Incidents & Events"]
)

app.include_router(
    tasks.router,
    prefix=f"{settings.api_v1_str}/tasks",
    tags=["Task Management"]
)

app.include_router(
    monitoring.router,
    prefix=f"{settings.api_v1_str}/monitoring",
    tags=["System Monitoring"]
)


# Development server entry point
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
