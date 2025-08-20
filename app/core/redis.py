"""
Redis connection and cache management.

This module provides Redis connection setup and cache operations
that integrate with the Celery task queue and FastAPI application.
"""

import redis
from typing import Optional, Any, Union
import json
from datetime import datetime, timedelta

from app.config.settings import settings


class RedisManager:
    """
    Redis connection manager with caching utilities.
    
    Provides connection management and common cache operations
    for the application's Redis integration.
    """
    
    def __init__(self):
        """Initialize Redis connection pool."""
        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,  # Automatically decode responses to strings
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value if found, None if not found or expired
        """
        try:
            value = self.redis_client.get(key)
            if value:
                # Try to deserialize JSON, fallback to string if not JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return None
        except redis.RedisError:
            # Log error in production, for now return None
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = 3600) -> bool:
        """
        Set value in Redis cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize complex objects as JSON
            if not isinstance(value, str):
                value = json.dumps(value, default=str)
            
            return self.redis_client.set(key, value, ex=ttl)
        except (redis.RedisError, TypeError):
            # Log error in production
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from Redis cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError:
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return bool(self.redis_client.exists(key))
        except redis.RedisError:
            return False
    
    def get_ttl(self, key: str) -> int:
        """
        Get time to live for a key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        try:
            return self.redis_client.ttl(key)
        except redis.RedisError:
            return -2
    
    def is_fresh(self, key: str, max_age_seconds: int = 3600) -> bool:
        """
        Check if cached data is fresh (within max age).
        
        Args:
            key: Cache key to check
            max_age_seconds: Maximum age in seconds for data to be considered fresh
            
        Returns:
            True if data exists and is fresh, False otherwise
        """
        if not self.exists(key):
            return False
        
        ttl = self.get_ttl(key)
        if ttl == -1:  # No expiry set
            return True
        if ttl == -2:  # Key doesn't exist
            return False
        
        # Calculate if remaining TTL indicates data is fresh
        # This is a simple heuristic - adjust based on your caching strategy
        return ttl > (max_age_seconds * 0.1)  # Fresh if >10% of max age remains


# Global Redis manager instance
redis_manager = RedisManager()


def get_redis() -> RedisManager:
    """
    FastAPI dependency function to get Redis manager.
    
    Returns:
        RedisManager: Redis connection manager instance
    """
    return redis_manager
