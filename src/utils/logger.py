"""
src/utils/logger.py

Provides a project-wide logger factory.

Every logger writes to:
  1. stdout  (INFO and above) — for live terminal feedback
  2. logs/pipeline.log (DEBUG and above) — rotating file, max 5 MB × 3 backups

The log level for the file handler can be overridden via the LOG_LEVEL
environment variable (default: DEBUG).
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_LOGS_DIR = "logs"
_LOG_FILE = os.path.join(_LOGS_DIR, "pipeline.log")
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
_BACKUP_COUNT = 3


def _ensure_log_dir() -> None:
    os.makedirs(_LOGS_DIR, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger configured with console + rotating-file handlers.

    Handlers are only added once per logger name (idempotent), so calling
    ``get_logger("foo")`` multiple times is safe.

    Args:
        name: Logger name — use the module / component name, e.g. ``"data_generator"``.

    Returns:
        A ``logging.Logger`` instance ready to use.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger   # already configured — skip re-adding handlers

    logger.setLevel(logging.DEBUG)

    _fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── 1. Console handler (INFO+) ──────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_fmt)
    logger.addHandler(console_handler)

    # ── 2. Rotating file handler (DEBUG+) ───────────────────────────────────
    try:
        _ensure_log_dir()
        file_level_str = os.environ.get("LOG_LEVEL", "DEBUG").upper()
        file_level = getattr(logging, file_level_str, logging.DEBUG)

        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(_fmt)
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as exc:
        # If we cannot write the log file, keep going with console-only
        logger.warning(f"Could not initialise file logger ({_LOG_FILE}): {exc}")

    return logger

