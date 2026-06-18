"""
log_factory.py
--------------
Provides a singleton LogFactory for creating and managing loggers
with consistent configuration across the application and Celery workers.
Uses `structlog` for structured, request-aware logging with JSON file
rotation and automatic HTML viewer generation.
"""

from structured_logging.config import LogConfigs, configure_logging  # Logging config and setup
from structured_logging.logger import AppLogger  # Application logger class
from datetime import datetime, timezone  # For timestamping log directories
import os  # OS utilities for directory management

# Define a local LOGS_PATH defaulted to a logs/ directory in the project root
LOGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))


class LogFactory:
    """
    Factory class to manage application-wide logging configuration 
    and provide specific logger instances for different services.
    """
    _instance = None

    def __new__(cls, logger_name=None, environment=None, log_level=None, log_dir=None, log_file_name=None):
        """Ensure only one instance of LogFactory exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(LogFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, logger_name=None, environment=None, log_level=None, log_dir=None, log_file_name=None):
        """
        Initialize LogFactory with logging settings. Skips re-initialization
        on subsequent calls (singleton behavior).

        Args:
            logger_name (str): Required name for the logger instance.
            environment (str): App environment (dev/prod).
            log_level (str): Logging level (INFO, DEBUG, etc.).
            log_dir (str): Directory to store log files.
            log_file_name (str): Log file name.
        """
        # Skip if already initialized
        if self._initialized:
            return

        if not logger_name:
            raise ValueError("logger_name is required for LogFactory")

        self.logger_name = logger_name
        self.environment = environment
        self.log_level = log_level
        self.log_dir = log_dir
        self.log_file_name = log_file_name
        self._loggers = {}  # Cache of service loggers
        self._initialized = True
        self._configure_logging()

    def _get_settings(self):
        """Build a LogConfigs object with current settings, using defaults for missing values."""
        return LogConfigs(
            logger_name=self.logger_name,
            environment=self.environment or "dev",
            log_level=self.log_level or "INFO",
            log_dir=self.log_dir or "logs",
            log_file_name=self.log_file_name or "application.log",
        )

    def _configure_logging(self):
        """Apply logging configuration using the current settings."""
        settings = self._get_settings()
        configure_logging(settings)

    def get_logger(self, service_name: str) -> AppLogger:
        """
        Get or create a logger for a specific service.

        Args:
            service_name (str): Name of the service requesting a logger.

        Returns:
            AppLogger: Logger instance for the given service.
        """
        if service_name not in self._loggers:
            self._loggers[service_name] = AppLogger(service_name, self._get_settings())
        return self._loggers[service_name]


# Global singleton instance for the LogFactory
log_factory = None


def init_log_factory(
    logger_name: str,
    environment=None,
    log_level=None,
    log_dir=None,
    log_file_name=None,
) -> LogFactory:
    """
    Initialize the global LogFactory singleton with the given settings.
    Ensures the log directory exists and configures logging for the app or worker.

    Args:
        logger_name (str): Name for the logger.
        environment (str): App environment.
        log_level (str): Logging level.
        log_dir (str): Custom log directory. If None, uses default with today's date.
        log_file_name (str): Log file name.

    Returns:
        LogFactory: The initialized LogFactory instance.
    """
    global log_factory
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Use user-provided log_dir, else default to LOGS_PATH/<today>
    if log_dir:
        log_dir = log_dir
    else:
        log_dir = os.path.join(LOGS_PATH, today)

    # Create the log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    log_factory = LogFactory(
        logger_name=logger_name,
        environment=environment,
        log_level=log_level,
        log_dir=log_dir,
        log_file_name=log_file_name,
    )
    return log_factory


def get_logger(service_name: str) -> AppLogger:
    """
    Get a logger for the given service name from the global LogFactory.

    Args:
        service_name (str): Name of the service requesting a logger.

    Returns:
        AppLogger: Logger instance for the given service.
    """
    global log_factory
    if log_factory is None:
        init_log_factory(logger_name="ingestion_service", environment="dev", log_level="INFO")
    return log_factory.get_logger(service_name)