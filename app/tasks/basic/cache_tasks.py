"""
Basic Redis cache operations with Celery.

This module demonstrates fundamental Celery tasks for cache management,
showcasing the integration between Celery workers and Redis cache operations.
"""

from celery import shared_task
from typing import Any, Optional, Dict, List
import json
from datetime import datetime, timedelta

from app.core.redis import redis_manager
from app.config.celery_config import celery_app


@shared_task(bind=True, name="cache.set_value")
def cache_set(self, key: str, value: Any, ttl: int = 3600) -> Dict[str, Any]:
    """
    Set a value in Redis cache with TTL.
    
    This task demonstrates basic cache write operations and provides
    detailed logging for monitoring cache performance.
    
    Args:
        key: Cache key to set
        value: Value to cache (JSON serializable)
        ttl: Time to live in seconds (default: 1 hour)
        
    Returns:
        Dict containing operation result and metadata
    """
    try:
        start_time = datetime.utcnow()
        
        # Attempt to set the cache value
        success = redis_manager.set(key, value, ttl)
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        result = {
            "success": success,
            "key": key,
            "ttl": ttl,
            "operation_time_ms": operation_time_ms,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        # Log success/failure
        if success:
            print(f"✅ Cache SET successful: {key} (TTL: {ttl}s, Time: {operation_time_ms:.2f}ms)")
        else:
            print(f"❌ Cache SET failed: {key}")
            
        return result
        
    except Exception as e:
        # Log error and re-raise for Celery retry mechanism
        print(f"💥 Cache SET error for key '{key}': {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@shared_task(bind=True, name="cache.get_value")
def cache_get(self, key: str) -> Dict[str, Any]:
    """
    Get a value from Redis cache.
    
    This task demonstrates cache read operations with hit/miss tracking
    and performance monitoring.
    
    Args:
        key: Cache key to retrieve
        
    Returns:
        Dict containing the cached value and metadata
    """
    try:
        start_time = datetime.utcnow()
        
        # Attempt to get the cache value
        value = redis_manager.get(key)
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Check TTL for freshness information
        ttl = redis_manager.get_ttl(key)
        
        result = {
            "key": key,
            "value": value,
            "found": value is not None,
            "ttl_remaining": ttl,
            "operation_time_ms": operation_time_ms,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        # Log cache hit/miss
        if value is not None:
            print(f"🎯 Cache HIT: {key} (TTL: {ttl}s, Time: {operation_time_ms:.2f}ms)")
        else:
            print(f"❌ Cache MISS: {key} (Time: {operation_time_ms:.2f}ms)")
            
        return result
        
    except Exception as e:
        print(f"💥 Cache GET error for key '{key}': {str(e)}")
        raise self.retry(exc=e, countdown=30, max_retries=3)


@shared_task(bind=True, name="cache.delete_value")
def cache_delete(self, key: str) -> Dict[str, Any]:
    """
    Delete a value from Redis cache.
    
    Args:
        key: Cache key to delete
        
    Returns:
        Dict containing operation result and metadata
    """
    try:
        start_time = datetime.utcnow()
        
        # Check if key exists before deletion
        existed = redis_manager.exists(key)
        
        # Delete the key
        success = redis_manager.delete(key)
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        result = {
            "key": key,
            "existed": existed,
            "deleted": success,
            "operation_time_ms": operation_time_ms,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        print(f"🗑️ Cache DELETE: {key} (Existed: {existed}, Deleted: {success}, Time: {operation_time_ms:.2f}ms)")
        
        return result
        
    except Exception as e:
        print(f"💥 Cache DELETE error for key '{key}': {str(e)}")
        raise self.retry(exc=e, countdown=30, max_retries=3)


@shared_task(bind=True, name="cache.bulk_set")
def cache_bulk_set(self, items: List[Dict[str, Any]], default_ttl: int = 3600) -> Dict[str, Any]:
    """
    Set multiple cache values in bulk.
    
    This task demonstrates batch operations and provides performance
    comparison between individual and bulk operations.
    
    Args:
        items: List of dicts with 'key', 'value', and optional 'ttl'
        default_ttl: Default TTL for items without specific TTL
        
    Returns:
        Dict containing bulk operation results
    """
    try:
        start_time = datetime.utcnow()
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for item in items:
            key = item['key']
            value = item['value']
            ttl = item.get('ttl', default_ttl)
            
            try:
                success = redis_manager.set(key, value, ttl)
                results.append({
                    "key": key,
                    "success": success,
                    "ttl": ttl
                })
                
                if success:
                    successful_count += 1
                else:
                    failed_count += 1
                    
            except Exception as item_error:
                failed_count += 1
                results.append({
                    "key": key,
                    "success": False,
                    "error": str(item_error)
                })
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        summary = {
            "total_items": len(items),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "operation_time_ms": operation_time_ms,
            "avg_time_per_item_ms": operation_time_ms / len(items) if items else 0,
            "results": results,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        print(f"📦 Cache BULK SET: {len(items)} items, {successful_count} success, {failed_count} failed (Time: {operation_time_ms:.2f}ms)")
        
        return summary
        
    except Exception as e:
        print(f"💥 Cache BULK SET error: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@shared_task(bind=True, name="cache.warm_up")
def cache_warm_up(self, cache_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Warm up cache with predefined data patterns.
    
    This task demonstrates proactive cache management, typically used
    during off-peak hours to prepare frequently accessed data.
    
    Args:
        cache_patterns: List of cache warming patterns with keys and data
        
    Returns:
        Dict containing cache warming results
    """
    try:
        start_time = datetime.utcnow()
        
        warmed_count = 0
        skipped_count = 0
        failed_count = 0
        
        for pattern in cache_patterns:
            key = pattern['key']
            data = pattern['data']
            ttl = pattern.get('ttl', 7200)  # Default 2 hours for warm-up
            force_update = pattern.get('force_update', False)
            
            try:
                # Check if key already exists (unless force update)
                if not force_update and redis_manager.exists(key):
                    # Check if data is still fresh
                    if redis_manager.is_fresh(key, max_age_seconds=ttl):
                        skipped_count += 1
                        continue
                
                # Set/update the cache
                success = redis_manager.set(key, data, ttl)
                
                if success:
                    warmed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as pattern_error:
                failed_count += 1
                print(f"⚠️ Cache warm-up failed for key '{key}': {str(pattern_error)}")
        
        end_time = datetime.utcnow()
        operation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        result = {
            "total_patterns": len(cache_patterns),
            "warmed_count": warmed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "operation_time_ms": operation_time_ms,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        print(f"🔥 Cache WARM-UP: {warmed_count} warmed, {skipped_count} skipped, {failed_count} failed (Time: {operation_time_ms:.2f}ms)")
        
        return result
        
    except Exception as e:
        print(f"💥 Cache WARM-UP error: {str(e)}")
        raise self.retry(exc=e, countdown=120, max_retries=2)


@shared_task(bind=True, name="cache.health_check")
def cache_health_check(self) -> Dict[str, Any]:
    """
    Perform Redis cache health check.
    
    This task verifies cache connectivity and performance,
    useful for monitoring and alerting systems.
    
    Returns:
        Dict containing cache health status and metrics
    """
    try:
        start_time = datetime.utcnow()
        
        # Test basic connectivity
        test_key = f"health_check_{self.request.id}"
        test_value = {"timestamp": start_time.isoformat(), "task_id": self.request.id}
        
        # Test SET operation
        set_start = datetime.utcnow()
        set_success = redis_manager.set(test_key, test_value, 60)
        set_time_ms = (datetime.utcnow() - set_start).total_seconds() * 1000
        
        # Test GET operation
        get_start = datetime.utcnow()
        retrieved_value = redis_manager.get(test_key)
        get_time_ms = (datetime.utcnow() - get_start).total_seconds() * 1000
        
        # Test DELETE operation
        delete_start = datetime.utcnow()
        delete_success = redis_manager.delete(test_key)
        delete_time_ms = (datetime.utcnow() - delete_start).total_seconds() * 1000
        
        end_time = datetime.utcnow()
        total_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Determine health status
        is_healthy = (
            set_success and 
            retrieved_value is not None and 
            delete_success and 
            total_time_ms < 1000  # Health check should complete within 1 second
        )
        
        result = {
            "healthy": is_healthy,
            "operations": {
                "set": {"success": set_success, "time_ms": set_time_ms},
                "get": {"success": retrieved_value is not None, "time_ms": get_time_ms},
                "delete": {"success": delete_success, "time_ms": delete_time_ms}
            },
            "total_time_ms": total_time_ms,
            "timestamp": start_time.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
        
        status_emoji = "✅" if is_healthy else "❌"
        print(f"{status_emoji} Cache HEALTH CHECK: {is_healthy} (Total time: {total_time_ms:.2f}ms)")
        
        return result
        
    except Exception as e:
        print(f"💥 Cache HEALTH CHECK error: {str(e)}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname
        }
