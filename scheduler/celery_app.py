from celery import Celery
from scheduler.scheduler_config import SchedulerConfig

# Initialize Celery with RabbitMQ broker
celery_app = Celery(
    "fhir_ingestion",
    broker=SchedulerConfig.CELERY_BROKER_URL,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,  # Fire-and-forget ingestion tasks: results not stored in queues
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Fair-distribution of tasks among worker processes
)
