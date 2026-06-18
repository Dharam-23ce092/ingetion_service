"""
logger.py
---------
Defines the AppLogger class for structured, request-aware logging.
Wraps structlog to provide per-service loggers with automatic
context binding, stacktrace resolution, and JSON output.
"""

from __future__ import annotations

from typing import Any
import structlog
from pathlib import Path
import traceback
from structured_logging.config import LogConfigs, get_request_context
from datetime import datetime, timezone

class MissingRequestIdError(ValueError):
    """Raised when a required request_id is missing from the logging context."""


def current_time():
    """
    Get the current time in UTC.

    Returns:
        datetime: Current time as a datetime object in UTC.
    """

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

class AppLogger:
    def __init__(self, name: str, settings: LogConfigs) -> None:
        """
        Initializes the logger for a specific service.
        """
        self._logger = structlog.get_logger(name)
        self._settings = settings
        self._name = name

    def _resolve_request_id(self, request_id: str | None) -> str:
        """
        Retrieves the request ID from the provided argument or the current execution context.
        Always returns a request_id.
        """
        if request_id:
            return str(request_id)

        ctx = get_request_context()
        ctx_request_id = ctx.get("request_id", "system")
        return str(ctx_request_id)

    def _event(
        self,
        *,
        level: str,
        message: str,
        request_id: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Internal helper to construct a structured log event dictionary.
        """
        resolved_request_id = self._resolve_request_id(request_id)
        data = {
            "timestamp": current_time(),
            "level": level.lower(),
            "message": message,
            "request_id": resolved_request_id,
            "logger_name": self._settings.logger_name,
            "environment": self._settings.environment,
            "service": self._name,
            "stacktrace": self._resolve_stacktrace(),
        }
        data.update(kwargs)
        return data

    def debug(self, message: str, *, request_id: str | None = None, **kwargs: Any) -> None:
        """Log a DEBUG-level message."""
        data = self._event(level="DEBUG", message=message, request_id=request_id, **kwargs)
        self._logger.debug(message, **data)

    def info(self, message: str, *, request_id: str | None = None, **kwargs: Any) -> None:
        """Log an INFO-level message."""
        data = self._event(level="INFO", message=message, request_id=request_id, **kwargs)
        self._logger.info(message, **data)

    def warning(self, message: str, *, request_id: str | None = None, **kwargs: Any) -> None:
        """Log a WARNING-level message."""
        data = self._event(level="WARNING", message=message, request_id=request_id, **kwargs)
        self._logger.warning(message, **data)

    def error(self, message: str, *, request_id: str | None = None, **kwargs: Any) -> None:
        """Log an ERROR-level message."""
        data = self._event(level="ERROR", message=message, request_id=request_id, **kwargs)
        self._logger.error(message, **data)

    def exception(self, message: str, *, request_id: str | None = None, **kwargs: Any) -> None:
        """Log an ERROR-level message with the current exception traceback."""
        data = self._event(level="ERROR", message=message, request_id=request_id, **kwargs)
        data["exception"] = traceback.format_exc()
        self._logger.error(message, **data)

    def _resolve_stacktrace(self) -> str:
        """
        Walk the call stack to find the caller's source location,
        skipping internal logging and third-party frames.

        Returns:
            str: A string like 'app.module.function:line' or empty string.
        """
        try:
            frames = traceback.extract_stack()
            cwd = Path.cwd().resolve()

            for frame in reversed(frames[:-2]):
                filename = frame.filename.replace("\\", "/").lower()

                if any(x in filename for x in ("site-packages", "venv", "appdata", "/python")):
                    continue

                try:
                    path = Path(frame.filename).resolve()
                    rel = path.relative_to(cwd)
                except ValueError:
                    continue

                module_path = ".".join(rel.with_suffix("").parts)

                if "structured_logging" in module_path:
                    continue

                return f"app.{module_path}.{frame.name}:{frame.lineno}"
        except Exception:
            pass

        return ""