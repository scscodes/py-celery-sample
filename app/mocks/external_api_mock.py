"""
External API Mock

Mock implementation for external REST APIs with configurable responses.
"""

import logging
import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ExternalAPIMock:
    """Mock external API implementation."""
    
    def __init__(self, failure_rate: float = 0.05):
        self.failure_rate = failure_rate
        self.response_delay = (0.1, 1.5)
        
        # Mock response mappings
        self._response_mappings = {}
        self._default_responses = {}
        
        # Request history
        self._request_history = []
        
        # Metrics
        self._request_count = 0
        self._error_count = 0
        
        logger.info("ExternalAPIMock initialized")
    
    async def make_request(self, method: str, url: str, headers: Dict = None, 
                          data: Any = None) -> Dict[str, Any]:
        """Make mock HTTP request."""
        start_time = time.time()
        self._request_count += 1
        
        try:
            await self._simulate_delay()
            
            if self._should_fail():
                self._error_count += 1
                raise Exception(f"HTTP {random.choice([500, 502, 503, 504])}: Service unavailable")
            
            # Check for mapped response
            response = self._get_mapped_response(method, url, data)
            
            # Store request history
            self._request_history.append({
                "method": method,
                "url": url,
                "headers": headers or {},
                "data": data,
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            execution_time = time.time() - start_time
            
            response.update({
                "execution_time_ms": execution_time * 1000,
                "request_id": f"req_{random.randint(100000, 999999)}"
            })
            
            logger.info(f"External API request: {method} {url}")
            return response
            
        except Exception as e:
            logger.error(f"External API request failed: {e}")
            raise
    
    def add_response_mapping(self, method: str, url_pattern: str, response: Dict[str, Any]) -> None:
        """Add custom response mapping."""
        key = f"{method}:{url_pattern}"
        self._response_mappings[key] = response
        logger.info(f"Added response mapping: {key}")
    
    def _get_mapped_response(self, method: str, url: str, data: Any) -> Dict[str, Any]:
        """Get mapped response or generate default."""
        key = f"{method}:{url}"
        
        if key in self._response_mappings:
            return self._response_mappings[key].copy()
        
        # Generate default response based on method
        if method == "GET":
            return {"status": 200, "data": {"result": "success", "items": []}}
        elif method == "POST":
            return {"status": 201, "data": {"id": random.randint(1000, 9999), "created": True}}
        elif method == "PUT":
            return {"status": 200, "data": {"updated": True}}
        elif method == "DELETE":
            return {"status": 204, "data": None}
        else:
            return {"status": 200, "data": {"result": "success"}}
    
    async def _simulate_delay(self) -> None:
        """Simulate API response time."""
        min_delay, max_delay = self.response_delay
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    def _should_fail(self) -> bool:
        """Determine if request should fail."""
        return random.random() < self.failure_rate
