"""
Redis Cache Mock

Mock implementation of Redis cache for testing and development.
"""

import logging
import asyncio
import random
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RedisMock:
    """Mock Redis implementation."""
    
    def __init__(self, failure_rate: float = 0.01):
        self.failure_rate = failure_rate
        self.response_delay = (0.001, 0.01)  # Very fast responses
        
        # In-memory storage
        self._data = {}
        self._expiry = {}
        
        # Metrics
        self._operations = 0
        self._hits = 0
        self._misses = 0
        
        logger.info("RedisMock initialized")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        await self._simulate_delay()
        self._operations += 1
        
        if self._should_fail():
            raise Exception("Redis connection error")
        
        # Check if key expired
        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
        
        if key in self._data:
            self._hits += 1
            return self._data[key]
        else:
            self._misses += 1
            return None
    
    async def set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set key-value pair with optional TTL."""
        await self._simulate_delay()
        self._operations += 1
        
        if self._should_fail():
            raise Exception("Redis connection error")
        
        self._data[key] = value
        
        if ttl:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        await self._simulate_delay()
        self._operations += 1
        
        if key in self._data:
            del self._data[key]
            if key in self._expiry:
                del self._expiry[key]
            return True
        return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        hit_rate = (self._hits / self._operations) if self._operations > 0 else 0
        
        return {
            "total_operations": self._operations,
            "cache_hits": self._hits,
            "cache_misses": self._misses,
            "hit_rate": hit_rate,
            "keys_stored": len(self._data),
            "memory_usage_keys": len(self._data)
        }
    
    async def _simulate_delay(self) -> None:
        """Simulate Redis response time."""
        min_delay, max_delay = self.response_delay
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    def _should_fail(self) -> bool:
        """Determine if operation should fail."""
        return random.random() < self.failure_rate
