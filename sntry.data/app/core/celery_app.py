"""
Celery configuration for background task processing with Redis broker
"""
import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure, task_retry
from app.core.config import settings

# Configure logging for Celery
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery instance with Redis broker
celery_app = Celery(
    "jamaica_business_directory",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.business_directory.tasks",
        "app.customer_360.tasks",
        "app.core.tasks"
    ]
)

# Enhanced Celery configuration with Redis broker
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="America/Jamaica",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Disable prefetching for fair distribution
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_disable_rate_limits=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to disk
    
    # Task routing with priority queues
    task_routes={
        # High priority scraping tasks
        "app.business_directory.tasks.scrape_full_website": {"queue": "scraping_high", "priority": 9},
        "app.business_directory.tasks.scrape_category": {"queue": "scraping_high", "priority": 8},
        
        # Regular scraping tasks
        "app.business_directory.tasks.scrape_*": {"queue": "scraping", "priority": 5},
        "app.business_directory.tasks.daily_scraping_task": {"queue": "scraping", "priority": 6},
        "app.business_directory.tasks.incremental_scraping_task": {"queue": "scraping", "priority": 5},
        
        # Geocoding tasks
        "app.business_directory.tasks.geocode_*": {"queue": "geocoding", "priority": 7},
        "app.business_directory.tasks.batch_geocoding_task": {"queue": "geocoding", "priority": 6},
        
        # Customer 360 tasks
        "app.customer_360.tasks.*": {"queue": "customer_360", "priority": 5},
        
        # Maintenance tasks (lower priority)
        "app.core.tasks.data_quality_check": {"queue": "maintenance", "priority": 3},
        "app.core.tasks.cleanup_inactive_businesses": {"queue": "maintenance", "priority": 2},
        "app.core.tasks.data_refresh_task": {"queue": "maintenance", "priority": 4},
    },
    
    # Queue configuration
    task_default_queue="default",
    task_default_exchange="default",
    task_default_exchange_type="direct",
    task_default_routing_key="default",
    
    # Retry configuration with exponential backoff
    task_default_retry_delay=60,  # 1 minute base delay
    task_max_retries=3,  # Maximum 3 retries
    task_retry_backoff=True,  # Enable exponential backoff
    task_retry_backoff_max=600,  # Maximum 10 minutes delay
    task_retry_jitter=True,  # Add randomness to retry delays
    
    # Redis broker specific settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_pool_limit=10,
    
    # Monitoring and visibility
    task_send_sent_event=True,  # Send task sent events
    worker_send_task_events=True,  # Send worker task events
    task_ignore_result=False,  # Store task results
    
    # Security
    task_always_eager=False,  # Execute tasks asynchronously
    task_store_eager_result=True,  # Store results even in eager mode
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Daily full scraping at 2 AM Jamaica time
    "daily-full-scraping": {
        "task": "app.business_directory.tasks.daily_scraping_task",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "scraping", "priority": 6}
    },
    
    # Incremental scraping every 4 hours
    "incremental-scraping": {
        "task": "app.business_directory.tasks.incremental_scraping_task", 
        "schedule": 14400.0,  # 4 hours
        "options": {"queue": "scraping", "priority": 5}
    },
    
    # Batch geocoding every hour
    "hourly-geocoding-batch": {
        "task": "app.business_directory.tasks.batch_geocoding_task",
        "schedule": 3600.0,  # 1 hour
        "options": {"queue": "geocoding", "priority": 6}
    },
    
    # Data quality check twice daily
    "data-quality-check": {
        "task": "app.core.tasks.data_quality_check",
        "schedule": 43200.0,  # 12 hours
        "options": {"queue": "maintenance", "priority": 3}
    },
    
    # Weekly cleanup of inactive businesses
    "weekly-cleanup": {
        "task": "app.core.tasks.cleanup_inactive_businesses",
        "schedule": 604800.0,  # 7 days
        "options": {"queue": "maintenance", "priority": 2}
    },
    
    # Daily data refresh for stale records
    "daily-data-refresh": {
        "task": "app.core.tasks.data_refresh_task",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "maintenance", "priority": 4}
    }
}

# Task monitoring and logging signals
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start"""
    logger.info(f"Task {task.name}[{task_id}] started with args={args}, kwargs={kwargs}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log task completion"""
    logger.info(f"Task {task.name}[{task_id}] completed with state={state}, result={retval}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Log task failures"""
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")
    logger.error(f"Traceback: {traceback}")

@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Log task retries"""
    logger.warning(f"Task {sender.name}[{task_id}] retry: {reason}")

# Health check task for monitoring
@celery_app.task(bind=True, name="celery.health_check")
def health_check(self):
    """Health check task for monitoring Celery workers"""
    return {"status": "healthy", "worker_id": self.request.id}