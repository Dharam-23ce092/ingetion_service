"""
schema.py
---------
Defines the TypedDict schema for structured log records.
Used to derive HTML viewer columns and validate log output format.
"""

from __future__ import annotations

from typing import Any, TypedDict


class LogRecordSchema(TypedDict, total=False):
    """
    Schema for a structured log record.
    All fields are optional (total=False) to allow partial log entries.
    """
    timestamp: str         # UTC timestamp of the log event
    level: str             # Log level (INFO, WARNING, ERROR)
    message: str           # Log message text
    request_id: str        # Request correlation ID
    service: str           # Service name that produced the log
    environment: str       # App environment (dev/prod)
    logger_name: str       # Logger instance name
    exception: str | None  # Exception traceback, if any
    
    # API Request Tracking Fields
    client_ip: str         # IP address of the caller
    request_path: str      # HTTP request path
    http_method: str       # HTTP method (GET, POST, etc.)
    status_code: int       # HTTP response status code
    duration_ms: float     # Request processing time in milliseconds
    user_id: str           # Authenticated user ID
    
    extra: dict[str, Any]  # Additional key-value pairs