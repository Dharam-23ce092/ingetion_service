# structured_logging package initializer
from structured_logging.config import LogConfigs, configure_logging, bind_request_context, clear_request_context  # Logging config and context helpers
from structured_logging.logger import AppLogger  # Application logger class
from structured_logging.log_factory import LogFactory, init_log_factory, get_logger  # Log factory and logger accessors

# Define the public API of the structured_logging package
__all__ = [
    "AppLogger",              # Main application logger class
    "LogConfigs",             # Logging configuration dataclass
    "bind_request_context",   # Bind request context for logs
    "clear_request_context",  # Clear request context
    "configure_logging",      # Configure structlog and stdlib logging
    "get_logger",             # Get a logger for a service
    "LogFactory",             # Logger factory singleton
    "init_log_factory",       # Initialize the logger factory
]