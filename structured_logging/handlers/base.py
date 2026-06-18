"""
Logging Handlers Base
=====================
Common mixins and utilities for custom logging handlers.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone


class DailyPathMixin:
    """
    Mixin to provide dated file paths for log storage.
    Automatically handles date formatting for daily rotation.
    """
    log_dir: str
    base_filename: str

    def get_dated_path(self, extension: str) -> tuple[str, str]:
        """
        Calculates the file path for the current UTC date.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{self.base_filename}-{today}.{extension}"
        return os.path.join(self.log_dir, filename), today