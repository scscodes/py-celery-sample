"""
Advanced Celery workflow orchestration patterns.

This module demonstrates complex workflow patterns using Celery's
group, chain, chord, and map primitives for enterprise orchestration.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import random
import time

from celery import group, chain, chord, signature
from celery.exceptions import Retry, Ignore
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# =============================================================================
# WORKFLOW BUILDING BLOCKS
# =============================================================================

@celery_app.task(bind=True, name="orchestration.validate_data")
def validate_data(self, data: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input data against business rules."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Validating data with rules: {rules}")
    
    # Simulate validation logic
    time.sleep(random.uniform(0.1, 0.5))
    
    errors = []
    validated_data = data.copy()
    
    # Example validation rules
    if rules.get("required_fields"):
        for field in rules["required_fields"]:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
    
    if rules.get("numeric_fields"):
        for field in rules["numeric_fields"]:
            if field in data and not isinstance(data[field], (int, float)):
                errors.append(f"Field {field} must be numeric")
    
    if errors:
        raise ValueError(f"Validation failed: {', '.join(errors)}")
    
    validated_data["validation_timestamp"] = datetime.utcnow().isoformat()
    validated_data["validator_task_id"] = task_id
    
    logger.info(f"[{task_id}] Validation successful")
    return validated_data


@celery_app.task(bind=True, name="orchestration.transform_data")
def transform_data(self, data: Dict[str, Any], transformation_config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform data according to configuration."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Transforming data with config: {transformation_config}")
    
    # Simulate transformation processing
    time.sleep(random.uniform(0.2, 0.8))
    
    transformed_data = data.copy()
    
    # Example transformations
    if transformation_config.get("uppercase_fields"):
        for field in transformation_config["uppercase_fields"]:
            if field in transformed_data and isinstance(transformed_data[field], str):
                transformed_data[field] = transformed_data[field].upper()
    
    if transformation_config.get("add_computed_fields"):
        for computed_field, formula in transformation_config["add_computed_fields"].items():
            if formula == "timestamp":
                transformed_data[computed_field] = datetime.utcnow().isoformat()
            elif formula == "uuid":
                import uuid
                transformed_data[computed_field] = str(uuid.uuid4())
    
    transformed_data["transformation_timestamp"] = datetime.utcnow().isoformat()
    transformed_data["transformer_task_id"] = task_id
    
    logger.info(f"[{task_id}] Transformation complete")
    return transformed_data


@celery_app.task(bind=True, name="orchestration.enrichment_lookup")
def enrichment_lookup(self, data: Dict[str, Any], lookup_config: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich data with external lookups."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Enriching data with config: {lookup_config}")
    
    # Simulate external API calls or database lookups
    time.sleep(random.uniform(0.3, 1.0))
    
    enriched_data = data.copy()
    
    # Simulate enrichment based on config
    if lookup_config.get("user_lookup") and "user_id" in data:
        enriched_data["user_details"] = {
            "name": f"User {data['user_id']}",
            "email": f"user{data['user_id']}@example.com",
            "role": random.choice(["admin", "user", "manager"])
        }
    
    if lookup_config.get("geo_lookup") and "ip_address" in data:
        enriched_data["geo_info"] = {
            "country": random.choice(["US", "UK", "DE", "FR", "JP"]),
            "city": random.choice(["New York", "London", "Berlin", "Paris", "Tokyo"]),
            "timezone": random.choice(["UTC-5", "UTC+0", "UTC+1", "UTC+1", "UTC+9"])
        }
    
    enriched_data["enrichment_timestamp"] = datetime.utcnow().isoformat()
    enriched_data["enrichment_task_id"] = task_id
    
    logger.info(f"[{task_id}] Enrichment complete")
    return enriched_data


@celery_app.task(bind=True, name="orchestration.save_to_storage")
def save_to_storage(self, data: Dict[str, Any], storage_config: Dict[str, Any]) -> Dict[str, Any]:
    """Save processed data to storage backend."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Saving data to storage: {storage_config}")
    
    # Simulate database/storage operations
    time.sleep(random.uniform(0.2, 0.6))
    
    storage_result = {
        "storage_id": f"doc_{random.randint(1000, 9999)}",
        "storage_backend": storage_config.get("backend", "default"),
        "saved_timestamp": datetime.utcnow().isoformat(),
        "saver_task_id": task_id,
        "data_size": len(json.dumps(data))
    }
    
    logger.info(f"[{task_id}] Save complete: {storage_result['storage_id']}")
    return storage_result


@celery_app.task(bind=True, name="orchestration.send_notification")
def send_notification(self, data: Dict[str, Any], notification_config: Dict[str, Any]) -> Dict[str, Any]:
    """Send notifications about completed processing."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Sending notification: {notification_config}")
    
    # Simulate notification sending
    time.sleep(random.uniform(0.1, 0.3))
    
    notification_result = {
        "notification_id": f"notif_{random.randint(1000, 9999)}",
        "recipient": notification_config.get("recipient", "admin@example.com"),
        "channel": notification_config.get("channel", "email"),
        "sent_timestamp": datetime.utcnow().isoformat(),
        "sender_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Notification sent: {notification_result['notification_id']}")
    return notification_result


# =============================================================================
# WORKFLOW PATTERNS
# =============================================================================

@celery_app.task(bind=True, name="orchestration.linear_workflow")
def linear_workflow(self, input_data: Dict[str, Any], workflow_config: Dict[str, Any]) -> str:
    """
    Execute a linear workflow using Celery chains.
    Each step depends on the previous step's output.
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting linear workflow with config: {workflow_config}")
    
    # Build the workflow chain
    workflow_chain = chain(
        validate_data.s(input_data, workflow_config.get("validation_rules", {})),
        transform_data.s(workflow_config.get("transformation_config", {})),
        enrichment_lookup.s(workflow_config.get("enrichment_config", {})),
        save_to_storage.s(workflow_config.get("storage_config", {}))
    )
    
    # Execute the chain
    result = workflow_chain.apply_async()
    
    logger.info(f"[{task_id}] Linear workflow chain started: {result.id}")
    return result.id


@celery_app.task(bind=True, name="orchestration.parallel_workflow")
def parallel_workflow(self, input_data: Dict[str, Any], workflow_config: Dict[str, Any]) -> str:
    """
    Execute parallel processing using Celery groups.
    Multiple independent tasks run simultaneously.
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting parallel workflow with config: {workflow_config}")
    
    # Validate data first
    validated_data = validate_data.apply_async(
        [input_data, workflow_config.get("validation_rules", {})]
    ).get()
    
    # Create parallel processing group
    parallel_group = group([
        transform_data.s(validated_data, workflow_config.get("transformation_config", {})),
        enrichment_lookup.s(validated_data, workflow_config.get("enrichment_config", {})),
    ])
    
    # Execute parallel tasks
    result = parallel_group.apply_async()
    
    logger.info(f"[{task_id}] Parallel workflow group started: {result.id}")
    return result.id


@celery_app.task(bind=True, name="orchestration.chord_workflow")
def chord_workflow(self, input_data: Dict[str, Any], workflow_config: Dict[str, Any]) -> str:
    """
    Execute a chord workflow: parallel tasks followed by a callback.
    Use when you need to aggregate results from parallel tasks.
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting chord workflow with config: {workflow_config}")
    
    # Validate data first
    validated_data = validate_data.apply_async(
        [input_data, workflow_config.get("validation_rules", {})]
    ).get()
    
    # Create chord: parallel tasks with callback
    workflow_chord = chord([
        transform_data.s(validated_data, workflow_config.get("transformation_config", {})),
        enrichment_lookup.s(validated_data, workflow_config.get("enrichment_config", {})),
    ])(aggregate_and_save.s(workflow_config.get("storage_config", {})))
    
    logger.info(f"[{task_id}] Chord workflow started: {workflow_chord.id}")
    return workflow_chord.id


@celery_app.task(bind=True, name="orchestration.aggregate_and_save")
def aggregate_and_save(self, parallel_results: List[Dict[str, Any]], storage_config: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate results from parallel tasks and save combined result."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Aggregating {len(parallel_results)} parallel results")
    
    # Combine all parallel results
    aggregated_data = {
        "aggregation_timestamp": datetime.utcnow().isoformat(),
        "aggregator_task_id": task_id,
        "source_count": len(parallel_results),
        "combined_data": {}
    }
    
    for i, result in enumerate(parallel_results):
        aggregated_data["combined_data"][f"source_{i}"] = result
    
    # Save aggregated result
    save_result = save_to_storage.apply_async([aggregated_data, storage_config]).get()
    
    logger.info(f"[{task_id}] Aggregation complete, saved as: {save_result['storage_id']}")
    return save_result


@celery_app.task(bind=True, name="orchestration.map_reduce_workflow")
def map_reduce_workflow(self, data_items: List[Dict[str, Any]], workflow_config: Dict[str, Any]) -> str:
    """
    Execute a map-reduce style workflow.
    Map: Process each item independently
    Reduce: Aggregate all results
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting map-reduce workflow for {len(data_items)} items")
    
    # Map phase: process each item in parallel
    map_tasks = [
        transform_data.s(item, workflow_config.get("transformation_config", {}))
        for item in data_items
    ]
    
    # Create map-reduce chord
    map_reduce_chord = chord(map_tasks)(
        reduce_results.s(workflow_config.get("reduce_config", {}))
    )
    
    logger.info(f"[{task_id}] Map-reduce workflow started: {map_reduce_chord.id}")
    return map_reduce_chord.id


@celery_app.task(bind=True, name="orchestration.reduce_results")
def reduce_results(self, mapped_results: List[Dict[str, Any]], reduce_config: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce/aggregate results from map phase."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Reducing {len(mapped_results)} mapped results")
    
    # Perform reduction based on config
    reduced_data = {
        "reduction_timestamp": datetime.utcnow().isoformat(),
        "reducer_task_id": task_id,
        "total_items": len(mapped_results),
        "reduction_type": reduce_config.get("type", "aggregate")
    }
    
    if reduce_config.get("type") == "sum" and reduce_config.get("field"):
        field = reduce_config["field"]
        total = sum(item.get(field, 0) for item in mapped_results if isinstance(item.get(field), (int, float)))
        reduced_data["sum_result"] = total
    
    elif reduce_config.get("type") == "count":
        reduced_data["count_result"] = len(mapped_results)
    
    else:  # Default aggregation
        reduced_data["aggregated_items"] = mapped_results
    
    logger.info(f"[{task_id}] Reduction complete")
    return reduced_data


# =============================================================================
# COMPLEX WORKFLOW ORCHESTRATOR
# =============================================================================

@celery_app.task(bind=True, name="orchestration.complex_workflow_orchestrator")
def complex_workflow_orchestrator(self, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute complex multi-stage workflows based on definition.
    
    Supports:
    - Conditional branching
    - Parallel stages
    - Error handling
    - Progress tracking
    - Dynamic workflow modification
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting complex workflow orchestration")
    
    # Initialize workflow state
    workflow_state = {
        "workflow_id": workflow_definition.get("id", f"workflow_{task_id}"),
        "started_at": datetime.utcnow().isoformat(),
        "orchestrator_task_id": task_id,
        "stages_completed": [],
        "current_stage": None,
        "status": "running",
        "results": {}
    }
    
    try:
        stages = workflow_definition.get("stages", [])
        input_data = workflow_definition.get("input_data", {})
        
        for stage_index, stage in enumerate(stages):
            stage_name = stage.get("name", f"stage_{stage_index}")
            workflow_state["current_stage"] = stage_name
            
            logger.info(f"[{task_id}] Executing stage: {stage_name}")
            
            # Execute stage based on type
            stage_type = stage.get("type", "sequential")
            
            if stage_type == "sequential":
                result = execute_sequential_stage(stage, input_data)
            elif stage_type == "parallel":
                result = execute_parallel_stage(stage, input_data)
            elif stage_type == "conditional":
                result = execute_conditional_stage(stage, input_data, workflow_state)
            else:
                raise ValueError(f"Unknown stage type: {stage_type}")
            
            # Store stage result
            workflow_state["results"][stage_name] = result
            workflow_state["stages_completed"].append(stage_name)
            
            # Update input_data for next stage if specified
            if stage.get("pass_output_to_next", False):
                input_data = result
        
        workflow_state["status"] = "completed"
        workflow_state["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"[{task_id}] Complex workflow completed successfully")
        
    except Exception as e:
        workflow_state["status"] = "failed"
        workflow_state["error"] = str(e)
        workflow_state["failed_at"] = datetime.utcnow().isoformat()
        logger.error(f"[{task_id}] Complex workflow failed: {e}")
        raise
    
    return workflow_state


def execute_sequential_stage(stage: Dict[str, Any], input_data: Dict[str, Any]) -> Any:
    """Execute a sequential stage with chained tasks."""
    tasks = stage.get("tasks", [])
    
    if not tasks:
        return input_data
    
    # Build chain of tasks
    task_signatures = []
    for task_def in tasks:
        task_name = task_def["name"]
        task_args = task_def.get("args", [])
        task_kwargs = task_def.get("kwargs", {})
        
        if task_name == "validate_data":
            task_signatures.append(validate_data.s(*task_args, **task_kwargs))
        elif task_name == "transform_data":
            task_signatures.append(transform_data.s(*task_args, **task_kwargs))
        elif task_name == "enrichment_lookup":
            task_signatures.append(enrichment_lookup.s(*task_args, **task_kwargs))
        elif task_name == "save_to_storage":
            task_signatures.append(save_to_storage.s(*task_args, **task_kwargs))
    
    if task_signatures:
        # Start chain with input data
        workflow_chain = chain(*task_signatures)
        return workflow_chain.apply_async([input_data]).get()
    
    return input_data


def execute_parallel_stage(stage: Dict[str, Any], input_data: Dict[str, Any]) -> List[Any]:
    """Execute a parallel stage with grouped tasks."""
    tasks = stage.get("tasks", [])
    
    if not tasks:
        return [input_data]
    
    # Build group of parallel tasks
    task_signatures = []
    for task_def in tasks:
        task_name = task_def["name"]
        task_args = task_def.get("args", [])
        task_kwargs = task_def.get("kwargs", {})
        
        if task_name == "transform_data":
            task_signatures.append(transform_data.s(input_data, *task_args, **task_kwargs))
        elif task_name == "enrichment_lookup":
            task_signatures.append(enrichment_lookup.s(input_data, *task_args, **task_kwargs))
    
    if task_signatures:
        parallel_group = group(task_signatures)
        return parallel_group.apply_async().get()
    
    return [input_data]


def execute_conditional_stage(stage: Dict[str, Any], input_data: Dict[str, Any], workflow_state: Dict[str, Any]) -> Any:
    """Execute a conditional stage based on workflow state."""
    condition = stage.get("condition", {})
    condition_type = condition.get("type", "always")
    
    should_execute = True
    
    if condition_type == "field_equals":
        field = condition["field"]
        expected_value = condition["value"]
        should_execute = input_data.get(field) == expected_value
    
    elif condition_type == "previous_stage_success":
        stage_name = condition["stage"]
        should_execute = stage_name in workflow_state["stages_completed"]
    
    if should_execute:
        return execute_sequential_stage(stage, input_data)
    else:
        return {"skipped": True, "reason": f"Condition not met: {condition}"}
