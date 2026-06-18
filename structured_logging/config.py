
# Import future annotations for forward reference support
from __future__ import annotations

# Standard library imports
import logging
from dataclasses import dataclass
import os
from typing import Any

# Third-party logging library
import structlog

# Local imports for custom handlers
from structured_logging.handlers import DailyFileHandler


# Dataclass to hold logging configuration values
@dataclass
class LogConfigs:
    logger_name: str  # Name of the logger instance
    environment: str = os.getenv("APP_ENV", "dev")  # App environment (dev/prod)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")  # Logging level (INFO, DEBUG, etc.)
    log_dir: str = os.getenv("LOG_DIR", "logs")  # Directory to store log files
    log_file_name: str = os.getenv("LOG_FILE_NAME", "application.log")  # Log file name

    def __post_init__(self) -> None:
        """
        Post-initialization to validate and normalize log level.
        """
        if not self.logger_name:
            raise ValueError("logger_name is required")
        self.log_level = self.log_level.upper()


def bind_request_context(request_id: str | None = None, **extra: Any) -> None:
    """
    Bind a request_id and any extra context to structlog's contextvars for request-scoped logging.
    """
    if request_id:
        structlog.contextvars.bind_contextvars(request_id=request_id, **extra)
    else:
        structlog.contextvars.bind_contextvars(**extra)


def clear_request_context() -> None:
    """
    Clear all structlog context variables (useful at the end of a request).
    """
    structlog.contextvars.clear_contextvars()


def get_request_context() -> dict[str, Any]:
    """
    Retrieve the current structlog context variables as a dictionary.
    """
    return dict(structlog.contextvars.get_contextvars())


def remove_structlog_event_key(
    _: Any, __: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Processor to rename the 'event' key to 'message' for log output consistency.
    """
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def ensure_log_dir(path: str) -> None:
    """
    Ensure the log directory exists; create it if it does not.
    """
    os.makedirs(path, exist_ok=True)


def configure_logging(settings: LogConfigs) -> None:
    """
    Main entry point for logging configuration.
    
    Sets up:
    1. Structlog processors for context merging and level adding.
    2. JSON formatting for persistent logs.
    3. Daily file rotation.
    4. HTML viewer scaffolding for the current day.
    """
    # Step 1: Ensure the physical log directory exists
    ensure_log_dir(settings.log_dir)

    # Step 2: Global structlog configuration
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Inject bind_request_context variables
            structlog.stdlib.add_log_level,           # Map structlog levels to stdlib levels
            remove_structlog_event_key,               # Align with 'message' field convention
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Step 3: Define the JSON formatter for file output
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            remove_structlog_event_key,
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),  # Render as machine-readable JSON
        ],
    )

    base_filename = settings.log_file_name.replace(".log", "")

    # Step 4: Setup the daily rotating JSON file handler
    json_handler = DailyFileHandler(
        log_dir=settings.log_dir,
        base_filename=base_filename,
    )
    json_handler.setFormatter(formatter)

    # Step 5: Configure the root logger to use our JSON handler
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(json_handler)
    
    # Add Console Handler
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            remove_structlog_event_key,
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),  # Render for console
        ],
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    root_logger.setLevel(settings.log_level.upper())
