import asyncio
import requests
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from structured_logging import get_logger
from scheduler.scheduler_config import SchedulerConfig

scheduler_logger = get_logger("scheduler_service")


class SchedulerService:
    def __init__(self):
        self._scheduler = AsyncIOScheduler()

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    async def start(self):
        """
        Registers the ingestion job on APScheduler using a cron trigger
        and starts the scheduler.
        """
        if not SchedulerConfig.SCHEDULER_ENABLED:
            scheduler_logger.info("Scheduler is disabled via config")
            return

        cron_trigger = CronTrigger(
            hour=SchedulerConfig.SCHEDULER_CRON_HOUR,
            minute=SchedulerConfig.SCHEDULER_CRON_MINUTE,
            day_of_week=SchedulerConfig.SCHEDULER_CRON_DAY_OF_WEEK,
        )

        self._scheduler.add_job(
            self._run_ingestion_job,
            trigger=cron_trigger,
            id="ingestion_cron_job",
            name="Patient Ingestion Cron Job",
            replace_existing=True,
        )

        self._scheduler.start()
        scheduler_logger.info(
            "Scheduler started",
            hour=SchedulerConfig.SCHEDULER_CRON_HOUR,
            minute=SchedulerConfig.SCHEDULER_CRON_MINUTE,
            day_of_week=SchedulerConfig.SCHEDULER_CRON_DAY_OF_WEEK,
        )

    async def stop(self):
        """
        Shuts down APScheduler cleanly on application shutdown.
        """
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            scheduler_logger.info("Scheduler service stopped")

    # ------------------------------------------------------------------ #
    #  Job entry-point (called by APScheduler on each cron tick)
    # ------------------------------------------------------------------ #

    async def _run_ingestion_job(self):
        """
        Top-level job that APScheduler invokes on every cron tick.
        """
        scheduler_logger.info("Cron tick — ingestion cycle started")

        try:
            await self.run_ingestion_for_all_users()
        except Exception as e:
            scheduler_logger.error("Unhandled error in ingestion cycle", error=str(e))

        scheduler_logger.info("Cron tick — ingestion cycle complete")

    # ------------------------------------------------------------------ #
    #  Core logic
    # ------------------------------------------------------------------ #

    async def run_ingestion_for_all_users(self):
        """
        1. Authenticate with central auth to get a client token.
        2. Fetch the list of registered users.
        3. Filter active users who have valid FHIR metadata.
        4. Process all of them concurrently via asyncio.gather.
        """
        scheduler_logger.info("Ingestion cycle started")

        # Step 1: Get client token
        scheduler_logger.info("Fetching client token from auth service")
        client_token = self._fetch_client_token()
        if not client_token:
            scheduler_logger.error("Failed to fetch client token, skipping cycle")
            return
        scheduler_logger.info("Client token received successfully")

        # Step 2: Get users list
        scheduler_logger.info("Fetching users list from auth service")
        users = self._fetch_users_list(client_token)
        if not users:
            scheduler_logger.warning("No users returned from auth service")
            return
        scheduler_logger.info("Users fetched successfully", total_users=len(users))

        # Step 3: Filter active users with valid FHIR metadata
        scheduler_logger.info("Filtering active users with valid FHIR metadata")
        valid_users_list = []
        seen_user_ids = set()
        for user in users:
            if not isinstance(user, dict):
                continue

            user_id = user.get("id")
            activated = user.get("activated", False)
            metadata = user.get("metadata")

            if not user_id or not activated or not isinstance(metadata, dict):
                continue

            if user_id in seen_user_ids:
                continue

            fhir_client_id = metadata.get("client_id")
            fhir_base_url = metadata.get("base_url")

            if not fhir_client_id or not fhir_base_url:
                continue

            seen_user_ids.add(user_id)
            valid_users_list.append({
                "user_id": user_id,
                "external_id": user.get("external_id", ""),
                "fhir_client_id": fhir_client_id,
                "fhir_base_url": fhir_base_url,
            })

        valid_users = tuple(valid_users_list)
        scheduler_logger.info("Active users filter complete", active_valid_users=len(valid_users))

        if not valid_users:
            scheduler_logger.warning("No active users with valid metadata to process")
            return

        for i, u in enumerate(valid_users, 1):
            scheduler_logger.info(
                "Valid user found for processing",
                user_index=i,
                external_id=u["external_id"],
                fhir_client_id=u["fhir_client_id"],
            )

        # Step 4: Run processing for each user in parallel via Celery (RabbitMQ)
        scheduler_logger.info(
            "Dispatching ingestion tasks to Celery queue",
            user_count=len(valid_users),
        )

        from scheduler.tasks import process_user_fhir_data_task

        for u in valid_users:
            process_user_fhir_data_task.delay(
                u["user_id"],
                u["fhir_client_id"],
                u["fhir_base_url"]
            )
            scheduler_logger.info(
                "Task dispatched to RabbitMQ broker",
                fhir_client_id=u["fhir_client_id"],
            )

        scheduler_logger.info("All user task dispatches completed")
        scheduler_logger.info("Ingestion cycle complete")

    # ------------------------------------------------------------------ #
    #  HTTP helpers
    # ------------------------------------------------------------------ #

    def _fetch_client_token(self) -> str:
        """
        POST /auth/token with client_id + client_secret_key to get
        an access_token from the central auth service.
        """
        url = f"{SchedulerConfig.AUTH_BASE_URL}/auth/token"

        try:
            client_id = int(SchedulerConfig.SCHEDULER_CLIENT_ID)
        except ValueError:
            client_id = SchedulerConfig.SCHEDULER_CLIENT_ID

        payload = {
            "client_id": client_id,
            "client_secret_key": SchedulerConfig.SCHEDULER_CLIENT_SECRET,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            token = response.json().get("access_token")
            if not token:
                scheduler_logger.error("Token response missing 'access_token' field")
                return ""
            return token
        except Exception as e:
            scheduler_logger.exception("Failed to fetch client token", error=str(e))
            return ""

    def _fetch_users_list(self, client_token: str) -> list:
        """
        GET /auth/users with Bearer token to retrieve all registered users.
        """
        url = f"{SchedulerConfig.AUTH_BASE_URL}/auth/users"
        headers = {
            "Authorization": f"Bearer {client_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                return data

            if isinstance(data, dict):
                for key in ("users", "data"):
                    if key in data and isinstance(data[key], list):
                        return data[key]

            scheduler_logger.error("Unexpected response shape from auth service", response_type=str(type(data)), url=url)
        except Exception as e:
            scheduler_logger.exception("Failed to fetch users list", error=str(e))

        return []


# Singleton
scheduler_service = SchedulerService()
