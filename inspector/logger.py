"""
logger.py

Central logging configuration for DevPilot System Inspector.

Every module obtains its logger via ``get_logger(__name__)``.
The root "devpilot" logger writes to both the rotating log file
(inside reports/) and to stderr at WARNING level so the console
stays quiet during normal operation.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from inspector.constants import LOG_FILE, REPORTS_DIR

# Ensure the reports directory exists before the file handler tries to open it.
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

_ROOT_LOGGER_NAME = "devpilot"
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB per log file
_BACKUP_COUNT = 3               # keep up to 3 rotated files

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure_root_logger() -> None:
    """
    Configure the "devpilot" root logger exactly once.

    File handler  — DEBUG and above, rotating, UTF-8.
    Console handler — WARNING and above (keeps CLI output clean).
    """
    root = logging.getLogger(_ROOT_LOGGER_NAME)

    if root.handlers:
        # Already configured; do not add duplicate handlers.
        return

    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    # Rotating file handler — full verbosity.
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler — warnings and errors only.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)


# Configure once at import time.
_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger of the "devpilot" hierarchy.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module, e.g.
        ``"inspector.cpu"``.  If the name does not start with the
        root logger name it is prepended automatically so that all
        SDK loggers form a single hierarchy.

    Returns
    -------
    logging.Logger
    """
    if not name.startswith(_ROOT_LOGGER_NAME):
        name = f"{_ROOT_LOGGER_NAME}.{name}"
    return logging.getLogger(name)
