"""
Main Celery application instance and task discovery.

This module creates the main Celery application instance and handles
automatic task discovery from all task modules. This is the entry point
for Celery workers and beat scheduler.
"""

from app.config.celery_config import celery_app

# Import all task modules to ensure they are registered with Celery
# This is important for auto-discovery to work properly

# Basic task modules
from app.tasks.basic import cache_tasks, crud_tasks

# Orchestration task modules (TODO: implement these)
from app.tasks.orchestration import workflow_tasks, monitoring_tasks, batch_tasks, retry_tasks

# Enterprise task modules (TODO: implement these)
# from app.tasks.enterprise import asset_sync, incident_workflows, reporting


# Export the main Celery app instance
# This is what workers will use: celery -A app.tasks.celery_app worker
__all__ = ["celery_app"]


# Optional: Add any startup hooks or custom configuration here
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Setup additional periodic tasks programmatically.
    
    This function is called after Celery configuration is complete
    and allows for dynamic task scheduling.
    """
    # Example: Add a dynamic periodic task
    # sender.add_periodic_task(30.0, test_task.s('periodic task test'))
    pass


@celery_app.task(bind=True)
def debug_task(self):
    """
    Debug task to test Celery functionality.
    
    This simple task can be used to verify that Celery is working
    correctly and workers can execute tasks.
    """
    print(f'Request: {self.request!r}')
    return f'Debug task executed successfully. Worker: {self.request.hostname}'


# Add some helper functions for task introspection
def get_registered_tasks():
    """
    Get list of all registered Celery tasks.
    
    Returns:
        list: List of task names registered with Celery
    """
    return list(celery_app.tasks.keys())


def get_active_workers():
    """
    Get information about active Celery workers.
    
    Returns:
        dict: Worker information from Celery inspect
    """
    inspect = celery_app.control.inspect()
    return inspect.active()


def get_task_stats():
    """
    Get task statistics from all workers.
    
    Returns:
        dict: Task statistics from Celery inspect
    """
    inspect = celery_app.control.inspect()
    return inspect.stats()
