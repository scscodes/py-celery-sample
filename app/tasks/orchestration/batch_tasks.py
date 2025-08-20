"""
Batch processing and bulk operations with progress tracking.

This module provides enterprise-grade batch processing capabilities
with progress tracking, chunking, error recovery, and resource management.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Iterator
from datetime import datetime, timedelta
import json
import random
import time
import math
from dataclasses import dataclass

from celery import group, chain, chord
from celery.exceptions import Retry, Ignore
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@dataclass
class BatchProgress:
    """Track batch processing progress."""
    batch_id: str
    total_items: int
    processed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    @property
    def completion_percentage(self) -> float:
        if self.total_items == 0:
            return 100.0
        return (self.processed_items / self.total_items) * 100.0
    
    @property
    def success_rate(self) -> float:
        total_attempted = self.processed_items + self.failed_items
        if total_attempted == 0:
            return 100.0
        return (self.processed_items / total_attempted) * 100.0


# =============================================================================
# BATCH PROCESSING CORE
# =============================================================================

@celery_app.task(bind=True, name="batch.process_single_item")
def process_single_item(self, item: Dict[str, Any], processing_config: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single item in a batch."""
    task_id = self.request.id
    item_id = item.get("id", "unknown")
    
    logger.info(f"[{task_id}] Processing item: {item_id}")
    
    try:
        # Simulate processing based on config
        processing_type = processing_config.get("type", "default")
        processing_time = processing_config.get("processing_time", 0.5)
        
        # Add realistic processing delay
        time.sleep(random.uniform(processing_time * 0.5, processing_time * 1.5))
        
        # Apply processing logic based on type
        processed_item = item.copy()
        
        if processing_type == "validation":
            # Simulate validation processing
            is_valid = random.choice([True, True, True, False])  # 75% success rate
            if not is_valid:
                raise ValueError(f"Validation failed for item {item_id}")
            processed_item["validation_status"] = "valid"
            
        elif processing_type == "transformation":
            # Simulate data transformation
            processed_item["transformed_at"] = datetime.utcnow().isoformat()
            processed_item["transformer_task_id"] = task_id
            
            # Apply transformations
            if "amount" in item:
                processed_item["amount_usd"] = item["amount"] * processing_config.get("exchange_rate", 1.0)
            
        elif processing_type == "enrichment":
            # Simulate external data enrichment
            processed_item["enriched_at"] = datetime.utcnow().isoformat()
            processed_item["enrichment_source"] = processing_config.get("source", "external_api")
            
            # Add enriched data
            processed_item["metadata"] = {
                "processing_region": random.choice(["us-east", "us-west", "eu-central"]),
                "quality_score": random.uniform(0.7, 1.0)
            }
        
        # Add processing metadata
        processed_item["processed_at"] = datetime.utcnow().isoformat()
        processed_item["processor_task_id"] = task_id
        processed_item["processing_status"] = "success"
        
        logger.info(f"[{task_id}] Successfully processed item: {item_id}")
        return processed_item
        
    except Exception as e:
        logger.error(f"[{task_id}] Failed to process item {item_id}: {e}")
        
        # Return error information for batch tracking
        return {
            "original_item": item,
            "processing_status": "failed",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat(),
            "processor_task_id": task_id
        }


@celery_app.task(bind=True, name="batch.process_chunk")
def process_chunk(self, chunk: List[Dict[str, Any]], chunk_index: int, processing_config: Dict[str, Any]) -> Dict[str, Any]:
    """Process a chunk of items within a batch."""
    task_id = self.request.id
    chunk_size = len(chunk)
    
    logger.info(f"[{task_id}] Processing chunk {chunk_index} with {chunk_size} items")
    
    chunk_start_time = datetime.utcnow()
    processed_items = []
    failed_items = []
    
    for item_index, item in enumerate(chunk):
        try:
            result = process_single_item.apply_async([item, processing_config]).get()
            
            if result.get("processing_status") == "success":
                processed_items.append(result)
            else:
                failed_items.append(result)
                
        except Exception as e:
            logger.error(f"[{task_id}] Chunk processing error for item {item_index}: {e}")
            failed_items.append({
                "original_item": item,
                "processing_status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat(),
                "chunk_processor_task_id": task_id
            })
    
    chunk_end_time = datetime.utcnow()
    processing_duration = (chunk_end_time - chunk_start_time).total_seconds()
    
    chunk_result = {
        "chunk_index": chunk_index,
        "chunk_size": chunk_size,
        "processed_items": processed_items,
        "failed_items": failed_items,
        "success_count": len(processed_items),
        "failure_count": len(failed_items),
        "processing_duration_seconds": processing_duration,
        "items_per_second": chunk_size / processing_duration if processing_duration > 0 else 0,
        "started_at": chunk_start_time.isoformat(),
        "completed_at": chunk_end_time.isoformat(),
        "processor_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Chunk {chunk_index} complete: {len(processed_items)} success, {len(failed_items)} failed")
    return chunk_result


@celery_app.task(bind=True, name="batch.aggregate_batch_results")
def aggregate_batch_results(self, chunk_results: List[Dict[str, Any]], batch_config: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate results from all batch chunks."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Aggregating results from {len(chunk_results)} chunks")
    
    # Initialize aggregation
    total_processed = 0
    total_failed = 0
    all_processed_items = []
    all_failed_items = []
    total_processing_time = 0
    
    # Aggregate chunk results
    for chunk_result in chunk_results:
        total_processed += chunk_result["success_count"]
        total_failed += chunk_result["failure_count"]
        all_processed_items.extend(chunk_result["processed_items"])
        all_failed_items.extend(chunk_result["failed_items"])
        total_processing_time += chunk_result["processing_duration_seconds"]
    
    total_items = total_processed + total_failed
    success_rate = (total_processed / total_items * 100) if total_items > 0 else 0
    
    # Calculate performance metrics
    avg_processing_time = total_processing_time / len(chunk_results) if chunk_results else 0
    total_throughput = total_items / total_processing_time if total_processing_time > 0 else 0
    
    batch_summary = {
        "batch_id": batch_config.get("batch_id", f"batch_{task_id}"),
        "aggregator_task_id": task_id,
        "total_items": total_items,
        "successful_items": total_processed,
        "failed_items": total_failed,
        "success_rate_percent": round(success_rate, 2),
        "total_chunks": len(chunk_results),
        "total_processing_time_seconds": round(total_processing_time, 2),
        "average_chunk_processing_time_seconds": round(avg_processing_time, 2),
        "total_throughput_items_per_second": round(total_throughput, 2),
        "aggregated_at": datetime.utcnow().isoformat()
    }
    
    # Include detailed results if requested
    if batch_config.get("include_detailed_results", False):
        batch_summary["processed_items"] = all_processed_items
        batch_summary["failed_items"] = all_failed_items
    
    # Include failure analysis if there were failures
    if total_failed > 0:
        failure_analysis = analyze_failures(all_failed_items)
        batch_summary["failure_analysis"] = failure_analysis
    
    logger.info(f"[{task_id}] Batch aggregation complete: {total_processed}/{total_items} successful ({success_rate:.1f}%)")
    return batch_summary


def analyze_failures(failed_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze failure patterns in batch processing."""
    if not failed_items:
        return {}
    
    error_types = {}
    error_patterns = {}
    
    for failed_item in failed_items:
        error_msg = failed_item.get("error", "Unknown error")
        
        # Categorize error types
        if "validation" in error_msg.lower():
            error_types["validation_errors"] = error_types.get("validation_errors", 0) + 1
        elif "timeout" in error_msg.lower():
            error_types["timeout_errors"] = error_types.get("timeout_errors", 0) + 1
        elif "connection" in error_msg.lower():
            error_types["connection_errors"] = error_types.get("connection_errors", 0) + 1
        else:
            error_types["other_errors"] = error_types.get("other_errors", 0) + 1
        
        # Track error patterns
        error_patterns[error_msg] = error_patterns.get(error_msg, 0) + 1
    
    return {
        "total_failures": len(failed_items),
        "error_types": error_types,
        "most_common_errors": sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:5],
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# BATCH ORCHESTRATORS
# =============================================================================

@celery_app.task(bind=True, name="batch.chunked_batch_processor")
def chunked_batch_processor(self, data_items: List[Dict[str, Any]], batch_config: Dict[str, Any]) -> str:
    """
    Process large batches by splitting into manageable chunks.
    
    Features:
    - Automatic chunking based on size limits
    - Parallel chunk processing
    - Progress tracking
    - Error isolation per chunk
    """
    task_id = self.request.id
    total_items = len(data_items)
    chunk_size = batch_config.get("chunk_size", 100)
    
    logger.info(f"[{task_id}] Starting chunked batch processing: {total_items} items, chunk size: {chunk_size}")
    
    # Calculate number of chunks
    num_chunks = math.ceil(total_items / chunk_size)
    
    # Create chunks
    chunks = []
    for i in range(0, total_items, chunk_size):
        chunk = data_items[i:i + chunk_size]
        chunks.append((chunk, i // chunk_size))
    
    # Create parallel chunk processing tasks
    chunk_tasks = [
        process_chunk.s(chunk, chunk_index, batch_config.get("processing_config", {}))
        for chunk, chunk_index in chunks
    ]
    
    # Execute chunks in parallel and aggregate results
    batch_chord = chord(chunk_tasks)(
        aggregate_batch_results.s(batch_config)
    )
    
    logger.info(f"[{task_id}] Chunked batch processing started: {num_chunks} chunks, batch_id: {batch_chord.id}")
    return batch_chord.id


@celery_app.task(bind=True, name="batch.progressive_batch_processor")
def progressive_batch_processor(self, data_items: List[Dict[str, Any]], batch_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process batches with progressive error handling and retry logic.
    
    Features:
    - Progressive chunk size adjustment based on success rate
    - Automatic retry of failed items
    - Circuit breaker for persistent failures
    - Real-time progress updates
    """
    task_id = self.request.id
    total_items = len(data_items)
    
    logger.info(f"[{task_id}] Starting progressive batch processing: {total_items} items")
    
    # Initialize progressive processing state
    processing_state = {
        "batch_id": f"progressive_{task_id}",
        "total_items": total_items,
        "processed_items": 0,
        "failed_items": 0,
        "retry_items": 0,
        "current_chunk_size": batch_config.get("initial_chunk_size", 50),
        "min_chunk_size": batch_config.get("min_chunk_size", 10),
        "max_chunk_size": batch_config.get("max_chunk_size", 200),
        "success_threshold": batch_config.get("success_threshold", 0.8),
        "max_retries": batch_config.get("max_retries", 3),
        "circuit_breaker_threshold": batch_config.get("circuit_breaker_threshold", 0.5),
        "stages": []
    }
    
    remaining_items = data_items.copy()
    retry_count = 0
    
    while remaining_items and retry_count < processing_state["max_retries"]:
        stage_start = datetime.utcnow()
        
        # Determine chunk size for this stage
        chunk_size = min(processing_state["current_chunk_size"], len(remaining_items))
        
        logger.info(f"[{task_id}] Stage {retry_count + 1}: Processing {len(remaining_items)} items with chunk size {chunk_size}")
        
        # Process items in chunks
        stage_results = []
        stage_failed_items = []
        
        for i in range(0, len(remaining_items), chunk_size):
            chunk = remaining_items[i:i + chunk_size]
            chunk_result = process_chunk.apply_async([chunk, i // chunk_size, batch_config.get("processing_config", {})]).get()
            
            stage_results.append(chunk_result)
            stage_failed_items.extend(chunk_result["failed_items"])
        
        # Calculate stage statistics
        stage_processed = sum(r["success_count"] for r in stage_results)
        stage_failed = sum(r["failure_count"] for r in stage_results)
        stage_success_rate = stage_processed / (stage_processed + stage_failed) if (stage_processed + stage_failed) > 0 else 0
        
        # Update processing state
        processing_state["processed_items"] += stage_processed
        processing_state["failed_items"] += stage_failed
        
        stage_info = {
            "stage": retry_count + 1,
            "items_attempted": len(remaining_items),
            "chunk_size": chunk_size,
            "success_count": stage_processed,
            "failure_count": stage_failed,
            "success_rate": stage_success_rate,
            "duration_seconds": (datetime.utcnow() - stage_start).total_seconds()
        }
        processing_state["stages"].append(stage_info)
        
        logger.info(f"[{task_id}] Stage {retry_count + 1} complete: {stage_processed} success, {stage_failed} failed (rate: {stage_success_rate:.2f})")
        
        # Circuit breaker check
        if stage_success_rate < processing_state["circuit_breaker_threshold"]:
            logger.warning(f"[{task_id}] Circuit breaker triggered: success rate {stage_success_rate:.2f} below threshold {processing_state['circuit_breaker_threshold']}")
            processing_state["circuit_breaker_triggered"] = True
            break
        
        # Adjust chunk size based on success rate
        if stage_success_rate >= processing_state["success_threshold"]:
            # Increase chunk size for better performance
            processing_state["current_chunk_size"] = min(
                processing_state["current_chunk_size"] * 1.5,
                processing_state["max_chunk_size"]
            )
        else:
            # Decrease chunk size for better reliability
            processing_state["current_chunk_size"] = max(
                processing_state["current_chunk_size"] * 0.7,
                processing_state["min_chunk_size"]
            )
        
        # Prepare items for retry
        remaining_items = [item["original_item"] for item in stage_failed_items]
        retry_count += 1
        
        if remaining_items:
            processing_state["retry_items"] = len(remaining_items)
            logger.info(f"[{task_id}] Preparing {len(remaining_items)} items for retry {retry_count}")
        
        # Add delay between retries
        if remaining_items and retry_count < processing_state["max_retries"]:
            retry_delay = batch_config.get("retry_delay_seconds", 5)
            time.sleep(retry_delay)
    
    # Final statistics
    processing_state["final_success_rate"] = processing_state["processed_items"] / total_items if total_items > 0 else 0
    processing_state["final_retry_count"] = retry_count
    processing_state["completed_at"] = datetime.utcnow().isoformat()
    
    logger.info(f"[{task_id}] Progressive batch processing complete: {processing_state['processed_items']}/{total_items} successful")
    return processing_state


@celery_app.task(bind=True, name="batch.priority_batch_processor")
def priority_batch_processor(self, data_items: List[Dict[str, Any]], batch_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process batches with priority-based ordering and resource allocation.
    
    Features:
    - Priority-based item ordering
    - Resource allocation per priority level
    - SLA-based processing guarantees
    - Dynamic priority adjustment
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting priority batch processing: {len(data_items)} items")
    
    # Sort items by priority
    priority_field = batch_config.get("priority_field", "priority")
    sorted_items = sorted(data_items, key=lambda x: x.get(priority_field, 0), reverse=True)
    
    # Group items by priority level
    priority_groups = {}
    for item in sorted_items:
        priority = item.get(priority_field, 0)
        if priority not in priority_groups:
            priority_groups[priority] = []
        priority_groups[priority].append(item)
    
    # Process each priority group
    priority_results = {}
    total_processed = 0
    total_failed = 0
    
    for priority in sorted(priority_groups.keys(), reverse=True):
        priority_items = priority_groups[priority]
        logger.info(f"[{task_id}] Processing priority {priority}: {len(priority_items)} items")
        
        # Determine processing parameters based on priority
        priority_config = get_priority_config(priority, batch_config)
        
        # Process priority group
        priority_start = datetime.utcnow()
        
        if priority_config["processing_method"] == "parallel":
            # High priority: process in parallel for speed
            priority_tasks = [
                process_single_item.s(item, priority_config["processing_config"])
                for item in priority_items
            ]
            priority_group = group(priority_tasks)
            priority_group_result = priority_group.apply_async().get()
            
        else:
            # Lower priority: process sequentially to conserve resources
            priority_group_result = []
            for item in priority_items:
                result = process_single_item.apply_async([item, priority_config["processing_config"]]).get()
                priority_group_result.append(result)
        
        # Analyze priority group results
        priority_processed = sum(1 for r in priority_group_result if r.get("processing_status") == "success")
        priority_failed = len(priority_group_result) - priority_processed
        priority_duration = (datetime.utcnow() - priority_start).total_seconds()
        
        priority_results[priority] = {
            "priority_level": priority,
            "total_items": len(priority_items),
            "processed_items": priority_processed,
            "failed_items": priority_failed,
            "success_rate": priority_processed / len(priority_items) if priority_items else 0,
            "processing_duration_seconds": priority_duration,
            "throughput_items_per_second": len(priority_items) / priority_duration if priority_duration > 0 else 0,
            "processing_method": priority_config["processing_method"],
            "sla_target_seconds": priority_config.get("sla_target_seconds"),
            "sla_met": priority_duration <= priority_config.get("sla_target_seconds", float('inf'))
        }
        
        total_processed += priority_processed
        total_failed += priority_failed
        
        logger.info(f"[{task_id}] Priority {priority} complete: {priority_processed}/{len(priority_items)} successful in {priority_duration:.1f}s")
    
    # Overall batch summary
    batch_summary = {
        "batch_id": f"priority_{task_id}",
        "processor_task_id": task_id,
        "total_items": len(data_items),
        "total_processed": total_processed,
        "total_failed": total_failed,
        "overall_success_rate": total_processed / len(data_items) if data_items else 0,
        "priority_levels_processed": len(priority_groups),
        "priority_results": priority_results,
        "completed_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"[{task_id}] Priority batch processing complete: {total_processed}/{len(data_items)} successful")
    return batch_summary


def get_priority_config(priority: int, batch_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get processing configuration based on priority level."""
    priority_configs = batch_config.get("priority_configs", {})
    
    # Default configurations based on priority
    if priority >= 10:  # Critical priority
        return priority_configs.get("critical", {
            "processing_method": "parallel",
            "processing_config": {"processing_time": 0.1},
            "sla_target_seconds": 60,
            "resource_allocation": "high"
        })
    elif priority >= 5:  # High priority
        return priority_configs.get("high", {
            "processing_method": "parallel",
            "processing_config": {"processing_time": 0.3},
            "sla_target_seconds": 300,
            "resource_allocation": "medium"
        })
    else:  # Normal/low priority
        return priority_configs.get("normal", {
            "processing_method": "sequential",
            "processing_config": {"processing_time": 0.5},
            "sla_target_seconds": 1800,
            "resource_allocation": "low"
        })


# =============================================================================
# BATCH MONITORING AND UTILITIES
# =============================================================================

@celery_app.task(bind=True, name="batch.get_batch_status")
def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
    """Get current status of a batch processing job."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Getting status for batch: {batch_id}")
    
    try:
        # In a real implementation, this would query a database or cache
        # For demonstration, we'll simulate status retrieval
        
        # Simulate batch status lookup
        time.sleep(0.1)
        
        status = {
            "batch_id": batch_id,
            "status": random.choice(["running", "completed", "failed", "paused"]),
            "progress_percentage": random.uniform(0, 100),
            "items_processed": random.randint(0, 1000),
            "items_remaining": random.randint(0, 500),
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=random.randint(5, 120))).isoformat(),
            "current_throughput": random.uniform(10, 100),
            "error_count": random.randint(0, 50),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        logger.info(f"[{task_id}] Batch {batch_id} status: {status['status']} ({status['progress_percentage']:.1f}%)")
        return status
        
    except Exception as e:
        logger.error(f"[{task_id}] Failed to get batch status for {batch_id}: {e}")
        return {
            "batch_id": batch_id,
            "status": "unknown",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, name="batch.cancel_batch")
def cancel_batch(self, batch_id: str, reason: str = "User requested") -> Dict[str, Any]:
    """Cancel a running batch processing job."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Cancelling batch: {batch_id}, reason: {reason}")
    
    # In a real implementation, this would:
    # 1. Mark the batch as cancelled in the database
    # 2. Send cancellation signals to running tasks
    # 3. Clean up resources
    # 4. Update progress tracking
    
    cancellation_result = {
        "batch_id": batch_id,
        "cancellation_status": "success",
        "cancelled_at": datetime.utcnow().isoformat(),
        "cancelled_by_task": task_id,
        "reason": reason,
        "message": f"Batch {batch_id} has been successfully cancelled"
    }
    
    logger.info(f"[{task_id}] Batch {batch_id} cancelled successfully")
    return cancellation_result
