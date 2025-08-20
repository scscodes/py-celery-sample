"""
Base Service Classes and Utilities

This module provides the foundation for all service layer implementations including
base classes, error handling, result types, and common service patterns.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar, Callable
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import asyncio
import inspect
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceError(Exception):
    """Base exception for service layer errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "SERVICE_ERROR"
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class ValidationError(ServiceError):
    """Validation error in service layer."""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field, "value": value})
        self.field = field
        self.value = value


class NotFoundError(ServiceError):
    """Resource not found error."""
    
    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} not found: {identifier}"
        super().__init__(message, "NOT_FOUND", {"resource_type": resource_type, "identifier": identifier})


class ConflictError(ServiceError):
    """Resource conflict error."""
    
    def __init__(self, message: str, conflicting_resource: str = None):
        super().__init__(message, "CONFLICT", {"conflicting_resource": conflicting_resource})


class AuthorizationError(ServiceError):
    """Authorization error."""
    
    def __init__(self, message: str, required_permission: str = None):
        super().__init__(message, "AUTHORIZATION_ERROR", {"required_permission": required_permission})


@dataclass
class ServiceResult(Generic[T]):
    """Standard result type for service operations."""
    success: bool
    data: Optional[T] = None
    error: Optional[ServiceError] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    def success_result(cls, data: T, metadata: Dict[str, Any] = None) -> 'ServiceResult[T]':
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata or {})
    
    @classmethod
    def error_result(cls, error: ServiceError, metadata: Dict[str, Any] = None) -> 'ServiceResult[T]':
        """Create an error result."""
        return cls(success=False, error=error, metadata=metadata or {})
    
    @classmethod
    def from_exception(cls, exc: Exception, metadata: Dict[str, Any] = None) -> 'ServiceResult[T]':
        """Create error result from exception."""
        if isinstance(exc, ServiceError):
            error = exc
        else:
            error = ServiceError(str(exc), "INTERNAL_ERROR")
        return cls.error_result(error, metadata)


def service_method(func: Callable) -> Callable:
    """Decorator for service methods with automatic error handling and logging."""
    
    @wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        method_name = f"{self.__class__.__name__}.{func.__name__}"
        logger.info(f"[{method_name}] Starting operation")
        
        try:
            # Validate service state
            if hasattr(self, '_validate_service_state'):
                self._validate_service_state()
            
            # Execute the method
            result = await func(self, *args, **kwargs)
            
            # Log success
            if isinstance(result, ServiceResult):
                if result.success:
                    logger.info(f"[{method_name}] Operation completed successfully")
                else:
                    logger.error(f"[{method_name}] Operation failed: {result.error.message}")
            else:
                logger.info(f"[{method_name}] Operation completed")
            
            return result
            
        except ServiceError as e:
            logger.error(f"[{method_name}] Service error: {e.message}")
            return ServiceResult.error_result(e)
        except Exception as e:
            logger.exception(f"[{method_name}] Unexpected error: {e}")
            error = ServiceError(f"Internal error in {method_name}: {str(e)}", "INTERNAL_ERROR")
            return ServiceResult.error_result(error)
    
    @wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        method_name = f"{self.__class__.__name__}.{func.__name__}"
        logger.info(f"[{method_name}] Starting operation")
        
        try:
            # Validate service state
            if hasattr(self, '_validate_service_state'):
                self._validate_service_state()
            
            # Execute the method
            result = func(self, *args, **kwargs)
            
            # Log success
            if isinstance(result, ServiceResult):
                if result.success:
                    logger.info(f"[{method_name}] Operation completed successfully")
                else:
                    logger.error(f"[{method_name}] Operation failed: {result.error.message}")
            else:
                logger.info(f"[{method_name}] Operation completed")
            
            return result
            
        except ServiceError as e:
            logger.error(f"[{method_name}] Service error: {e.message}")
            return ServiceResult.error_result(e)
        except Exception as e:
            logger.exception(f"[{method_name}] Unexpected error: {e}")
            error = ServiceError(f"Internal error in {method_name}: {str(e)}", "INTERNAL_ERROR")
            return ServiceResult.error_result(error)
    
    # Return appropriate wrapper based on whether function is async
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class BaseService(ABC):
    """Abstract base class for all services."""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"services.{self.name}")
        self._initialized = False
        self._dependencies = {}
        self._configuration = {}
        
    def initialize(self, config: Dict[str, Any] = None) -> None:
        """Initialize the service with configuration."""
        self._configuration = config or {}
        self._initialized = True
        self.logger.info(f"Service {self.name} initialized")
    
    def _validate_service_state(self) -> None:
        """Validate that the service is properly initialized."""
        if not self._initialized:
            raise ServiceError(f"Service {self.name} not initialized", "SERVICE_NOT_INITIALIZED")
    
    def add_dependency(self, name: str, service: 'BaseService') -> None:
        """Add a service dependency."""
        self._dependencies[name] = service
        self.logger.debug(f"Added dependency: {name}")
    
    def get_dependency(self, name: str) -> 'BaseService':
        """Get a service dependency."""
        if name not in self._dependencies:
            raise ServiceError(f"Dependency {name} not found", "DEPENDENCY_NOT_FOUND")
        return self._dependencies[name]
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get service configuration."""
        return self._configuration
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._configuration.get(key, default)


class CachedService(BaseService):
    """Base service with caching capabilities."""
    
    def __init__(self, name: str = None, cache_ttl: int = 300):
        super().__init__(name)
        self._cache = {}
        self._cache_ttl = cache_ttl
    
    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        return ":".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if datetime.utcnow().timestamp() - cached_item["timestamp"] < self._cache_ttl:
                return cached_item["value"]
            else:
                # Remove expired item
                del self._cache[cache_key]
        return None
    
    def _put_in_cache(self, cache_key: str, value: Any) -> None:
        """Put value in cache with timestamp."""
        self._cache[cache_key] = {
            "value": value,
            "timestamp": datetime.utcnow().timestamp()
        }
    
    def _clear_cache(self, pattern: str = None) -> None:
        """Clear cache entries, optionally matching pattern."""
        if pattern is None:
            self._cache.clear()
            self.logger.info("Cache cleared")
        else:
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self._cache[key]
            self.logger.info(f"Cache cleared for pattern: {pattern}")


class AsyncService(BaseService):
    """Base service for async operations."""
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self, 'cleanup'):
            await self.cleanup()


class EventEmitter:
    """Simple event emitter for service events."""
    
    def __init__(self):
        self._listeners = {}
    
    def on(self, event: str, callback: Callable) -> None:
        """Register event listener."""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def off(self, event: str, callback: Callable) -> None:
        """Unregister event listener."""
        if event in self._listeners:
            try:
                self._listeners[event].remove(callback)
            except ValueError:
                pass
    
    async def emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to all listeners."""
        if event in self._listeners:
            for callback in self._listeners[event]:
                try:
                    if inspect.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event listener for {event}: {e}")


@dataclass
class ServiceHealth:
    """Service health information."""
    service_name: str
    healthy: bool
    status: str
    last_check: datetime
    response_time_ms: float
    dependencies: Dict[str, bool]
    metrics: Dict[str, Any]


class HealthCheckService(BaseService):
    """Service for health checking other services."""
    
    def __init__(self):
        super().__init__("HealthCheckService")
        self._services = {}
    
    def register_service(self, service: BaseService) -> None:
        """Register a service for health checking."""
        self._services[service.name] = service
    
    @service_method
    async def check_service_health(self, service_name: str) -> ServiceResult[ServiceHealth]:
        """Check health of a specific service."""
        if service_name not in self._services:
            raise NotFoundError("Service", service_name)
        
        service = self._services[service_name]
        start_time = datetime.utcnow()
        
        try:
            # Basic health check - verify service is initialized
            service._validate_service_state()
            
            # Check dependencies if available
            dependency_health = {}
            for dep_name, dep_service in service._dependencies.items():
                try:
                    dep_service._validate_service_state()
                    dependency_health[dep_name] = True
                except:
                    dependency_health[dep_name] = False
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            health = ServiceHealth(
                service_name=service_name,
                healthy=True,
                status="healthy",
                last_check=end_time,
                response_time_ms=response_time,
                dependencies=dependency_health,
                metrics={"uptime": "unknown"}  # Could be enhanced
            )
            
            return ServiceResult.success_result(health)
            
        except Exception as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            health = ServiceHealth(
                service_name=service_name,
                healthy=False,
                status=f"unhealthy: {str(e)}",
                last_check=end_time,
                response_time_ms=response_time,
                dependencies={},
                metrics={}
            )
            
            return ServiceResult.success_result(health)
    
    @service_method
    async def check_all_services(self) -> ServiceResult[Dict[str, ServiceHealth]]:
        """Check health of all registered services."""
        health_results = {}
        
        for service_name in self._services.keys():
            result = await self.check_service_health(service_name)
            if result.success:
                health_results[service_name] = result.data
        
        return ServiceResult.success_result(health_results)


# Service registry for dependency injection
class ServiceRegistry:
    """Simple service registry for dependency injection."""
    
    def __init__(self):
        self._services = {}
        self._singletons = {}
    
    def register(self, service_type: type, implementation: BaseService = None, singleton: bool = True) -> None:
        """Register a service implementation."""
        self._services[service_type] = implementation or service_type
        if singleton and implementation:
            self._singletons[service_type] = implementation
    
    def get(self, service_type: type) -> BaseService:
        """Get service instance."""
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        if service_type in self._services:
            implementation = self._services[service_type]
            if isinstance(implementation, type):
                # Create new instance
                instance = implementation()
                if service_type in self._singletons:
                    self._singletons[service_type] = instance
                return instance
            else:
                return implementation
        
        raise ServiceError(f"Service not registered: {service_type}", "SERVICE_NOT_REGISTERED")
    
    def create_scope(self) -> 'ServiceRegistry':
        """Create a new scope for scoped services."""
        scope = ServiceRegistry()
        scope._services = self._services.copy()
        # Don't copy singletons to scope
        return scope


# Global service registry
service_registry = ServiceRegistry()
