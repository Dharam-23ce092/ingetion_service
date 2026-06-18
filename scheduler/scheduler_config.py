import os


class SchedulerConfig:
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "True").lower() == "true"
    SCHEDULER_CLIENT_ID = os.getenv("SCHEDULER_CLIENT_ID", "")
    SCHEDULER_CLIENT_SECRET = os.getenv("SCHEDULER_CLIENT_SECRET", "")
    AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "https://aibot.meditab.com").rstrip("/")

    # Cron schedule fields (default: every day at 6:00 AM)
    SCHEDULER_CRON_HOUR = os.getenv("SCHEDULER_CRON_HOUR", "6")
    SCHEDULER_CRON_MINUTE = os.getenv("SCHEDULER_CRON_MINUTE", "0")
    SCHEDULER_CRON_DAY_OF_WEEK = os.getenv("SCHEDULER_CRON_DAY_OF_WEEK", "*")

    # Max concurrent threads for parallel ingestion processing
    SCHEDULER_MAX_WORKERS = int(os.getenv("SCHEDULER_MAX_WORKERS", "5"))

    # Celery settings
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")

