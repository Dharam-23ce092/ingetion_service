import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from structured_logging import init_log_factory
from scheduler.scheduler_service import scheduler_service


def init_logging():
    # Initialize the structured log factory
    init_log_factory(
        logger_name="ingestion_service",
        environment=os.getenv("APP_ENV", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir=os.getenv("LOG_DIR", "logs"),
        log_file_name=os.getenv("LOG_FILE_NAME", "ingestion.log"),
    )


async def main():
    init_logging()
    
    # Start the background scheduler trigger
    await scheduler_service.start()
    
    # Keep the server running continuously
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await scheduler_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
