import time
import requests
from scheduler.celery_app import celery_app
from structured_logging import get_logger

tasks_logger = get_logger("celery_tasks")


class IngestionTask(celery_app.Task):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Executed when a task runs out of retries or fails with a non-retryable exception."""
        fhir_client_id = args[1] if len(args) > 1 else "unknown"
        tasks_logger.error(
            "FHIR Ingestion Task Permanently Failed",
            task_id=task_id,
            fhir_client_id=fhir_client_id,
            error=str(exc),
            traceback=str(einfo),
        )


@celery_app.task(
    bind=True,
    base=IngestionTask,
    # Automatically retry for HTTP connection/timeout errors or standard connection exceptions
    autoretry_for=(
        requests.exceptions.RequestException,
        ConnectionError,
        TimeoutError,
    ),
    retry_kwargs={"max_retries": 2, "countdown": 5},  # Initial wait of 5 seconds
    retry_backoff=True,  # Backoff: 5s, 10s, 20s...
    retry_backoff_max=60,  # Cap delay at 60 seconds
)
def process_user_fhir_data_task(
    self, user_id: str, fhir_client_id: str, fhir_base_url: str
):
    """Celery task that runs the FHIR ingestion logic for a single user."""
    tasks_logger.info(
        "Celery FHIR Ingestion Task Started",
        fhir_client_id=fhir_client_id,
        attempt=self.request.retries + 1,
    )

    # Simulated network latency of FHIR call.
    # The other developer will replace this with actual FHIR integration code.
    time.sleep(2)

    # Success Log
    tasks_logger.info(
        "Celery FHIR Ingestion Task Completed Successfully",
        fhir_client_id=fhir_client_id,
    )
    return {"user_id": user_id, "status": "SUCCESS"}
