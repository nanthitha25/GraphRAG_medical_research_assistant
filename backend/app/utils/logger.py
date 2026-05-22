"""
app/utils/logger.py
-------------------
Structured logging factory for the GraphRAG Medical Research Assistant.

Every log record is emitted as a single-line JSON object containing at least:
  * ``timestamp``  – ISO-8601 UTC timestamp
  * ``level``      – log level name (INFO, WARNING, ERROR, …)
  * ``module``     – logger name passed to :func:`get_logger`
  * ``message``    – the formatted log message
  * any extra keyword arguments passed via ``extra={"key": value}``

Two handlers are attached to each logger:
  1. :class:`logging.handlers.RotatingFileHandler`
     – writes to ``logs/graphrag.log`` (10 MB per file, 5 backups)
  2. :class:`logging.StreamHandler`
     – writes to *stdout*

The ``logs/`` directory is created automatically if it does not exist.

Usage
-----
    from app.utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Pipeline started", extra={"source_pdf": "paper.pdf", "chunk_id": 42})
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.config import get_config

# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


class _JsonFormatter(logging.Formatter):
    """Format every :class:`logging.LogRecord` as a compact JSON line.

    Standard fields are always present.  Any extra key/value pairs placed in
    ``record.__dict__`` by a caller using ``extra={...}`` are merged in as
    well, provided they do not shadow the standard fields.
    """

    # Keys that belong to the standard LogRecord and should not be treated as
    # application-level "extra" fields.
    _STDLIB_KEYS: frozenset[str] = frozenset(
        {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        """Return a JSON-serialised string for *record*."""
        # Ensure record.message is populated.
        record.message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.message,
        }

        # Merge caller-supplied extra fields.
        for key, value in record.__dict__.items():
            if key not in self._STDLIB_KEYS and not key.startswith("_"):
                payload[key] = value

        # Append exception info when present.
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Logger registry  (module-level cache so handlers are not added twice)
# ---------------------------------------------------------------------------

_registry: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Return a named :class:`logging.Logger` with JSON + rotating-file output.

    Calling this function multiple times with the same *name* returns the
    **same** logger object (no duplicate handlers are added).

    Parameters
    ----------
    name:
        Logger name – typically ``__name__`` of the calling module.

    Returns
    -------
    logging.Logger
        Fully configured logger ready for use.
    """
    if name in _registry:
        return _registry[name]

    cfg = get_config()

    # ------------------------------------------------------------------ #
    # Resolve log level
    # ------------------------------------------------------------------ #
    numeric_level: int = getattr(logging, cfg.log_level, logging.INFO)

    # ------------------------------------------------------------------ #
    # Ensure the logs/ directory exists
    # ------------------------------------------------------------------ #
    log_path = Path(cfg.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Build the logger
    # ------------------------------------------------------------------ #
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    # Prevent log records from propagating to the root logger, which would
    # cause duplicate output when multiple named loggers are active.
    logger.propagate = False

    if logger.handlers:
        # Already configured by a previous call (e.g. via the root logger).
        _registry[name] = logger
        return logger

    formatter = _JsonFormatter()

    # ------------------------------------------------------------------ #
    # Handler 1 – Rotating file
    # ------------------------------------------------------------------ #
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_path),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    # ------------------------------------------------------------------ #
    # Handler 2 – stdout stream
    # ------------------------------------------------------------------ #
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    _registry[name] = logger
    return logger
