from __future__ import annotations

import logging
from typing import Any

from structured_logging.handlers.base import DailyPathMixin


class DailyFileHandler(DailyPathMixin, logging.Handler):
    """
    A lightweight rotating file handler that writes logs into files 
    named with the current date (e.g., application-2024-03-20.log).
    Automatically switches to a new file when the date changes.
    """

    def __init__(self, log_dir: str, base_filename: str):
        super().__init__()
        self.log_dir = log_dir
        self.base_filename = base_filename
        self.current_date: str | None = None
        self.stream: Any = None

    def _open_new_file(self) -> None:
        """Close the current log file (if open) and open a new dated log file."""
        if self.stream:
            self.stream.close()

        filepath, today = self.get_dated_path("log")
        self.stream = open(filepath, "a", encoding="utf-8")
        self.current_date = today

    def emit(self, record: logging.LogRecord) -> None:
        """
        Write a log record to the current daily log file.
        Rotates the file if the date has changed since last write.
        """
        try:
            _, today = self.get_dated_path("log")

            if self.current_date != today:
                self._open_new_file()

            msg = self.format(record)
            self.stream.write(msg + "\n")
            self.stream.flush()
        except Exception:
            self.handleError(record)