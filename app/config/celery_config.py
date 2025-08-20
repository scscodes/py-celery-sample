"""
Celery configuration and setup.

This module configures Celery with Redis broker, result backend,
and all the settings needed for the Celery showcase workflows.
"""

from celery import Celery
from kombu import Queue
from datetime import timedelta

from app.config.settings import settings


def make_celery() -> Celery:
    """
    Create and configure Celery application instance.
    
    Returns:
        Celery: Configured Celery application
    """
    # Create Celery instance with custom name
    celery_app = Celery("celery_showcase")
    
    # Basic Celery configuration
    celery_app.conf.update(
        # Broker and Result Backend
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,
        
        # Task Serialization
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        
        # Results Configuration
        result_expires=3600,  # Results expire after 1 hour
        result_persistent=True,  # Store results persistently
        
        # Task Routing and Queues
        task_routes={
            # Basic tasks go to default queue
            "app.tasks.basic.*": {"queue": "default"},
            # Orchestration tasks get higher priority
            "app.tasks.orchestration.*": {"queue": "orchestration", "priority": 5},
            # Enterprise tasks get dedicated queue
            "app.tasks.enterprise.*": {"queue": "enterprise", "priority": 3},
        },
        
        # Define task queues with different priorities
        task_queues=(
            Queue("default", priority=1),
            Queue("orchestration", priority=5),
            Queue("enterprise", priority=3),
        ),
        
        # Worker Configuration
        worker_prefetch_multiplier=1,  # Prevent worker from hoarding tasks
        task_acks_late=True,  # Acknowledge tasks after completion
        worker_disable_rate_limits=False,
        
        # Task Execution Configuration
        task_always_eager=False,  # Set to True for testing without worker
        task_eager_propagates=True,  # Propagate exceptions in eager mode
        task_ignore_result=False,  # Store task results
        
        # Retry Configuration
        task_default_retry_delay=60,  # 1 minute default retry delay
        task_max_retries=3,  # Maximum retry attempts
        
        # Time Limits
        task_soft_time_limit=300,  # 5 minutes soft limit
        task_time_limit=600,  # 10 minutes hard limit
        
        # Monitoring and Logging
        worker_send_task_events=True,  # Enable task events for monitoring
        task_send_sent_event=True,  # Send task-sent events
        
        # Beat Schedule (for periodic tasks)
        beat_schedule={
            # Periodic tasks disabled until orchestration modules are activated
            # Uncomment and configure these when ready to use Celery Beat
            
            # 'periodic-health-check': {
            #     'task': 'monitoring.system_health_check',  # Corrected task name
            #     'schedule': timedelta(minutes=5),
            #     'options': {'queue': 'orchestration'}
            # },
            
            # 'daily-system-report': {
            #     'task': 'app.tasks.enterprise.reporting.generate_daily_report',
            #     'schedule': timedelta(hours=24),
            #     'options': {'queue': 'enterprise'}
            # },
        },
        
        # Timezone for beat scheduler
        timezone='UTC',
        
        # Security Configuration
        worker_hijack_root_logger=False,
        worker_log_color=True,
    )
    
    # Auto-discover tasks from all modules
    # This will automatically find all tasks defined in the tasks modules
    celery_app.autodiscover_tasks([
        'app.tasks.basic',
        'app.tasks.orchestration', 
        'app.tasks.enterprise'
    ])
    
    return celery_app


# Create the global Celery instance
celery_app = make_celery()


# Celery configuration for different task types
class CeleryConfig:
    """
    Advanced Celery configuration options for different scenarios.
    
    This class provides pre-configured settings for different types
    of Celery deployments and use cases.
    """
    
    @staticmethod
    def get_development_config():
        """Configuration optimized for development."""
        return {
            'task_always_eager': False,  # Use actual workers even in dev
            'task_eager_propagates': True,
            'worker_log_level': 'DEBUG',
            'worker_concurrency': 2,  # Lower concurrency for dev
        }
    
    @staticmethod
    def get_production_config():
        """Configuration optimized for production."""
        return {
            'task_always_eager': False,
            'worker_log_level': 'INFO',
            'worker_concurrency': 4,  # Higher concurrency for production
            'task_compression': 'gzip',  # Compress task messages
            'result_compression': 'gzip',  # Compress results
        }
    
    @staticmethod
    def get_testing_config():
        """Configuration for testing (synchronous execution)."""
        return {
            'task_always_eager': True,  # Execute tasks synchronously
            'task_eager_propagates': True,
            'broker_url': 'memory://',  # In-memory broker for tests
            'result_backend': 'cache+memory://',  # In-memory results
        }
