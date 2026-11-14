"""
Zohra — Structured logging with sensitive-data redaction.

Log format:
  - Development: human-readable coloured output
  - Production / Testing: JSON structured logs

Every log entry can carry contextual fields (request_id, job_id,
agent_run_id, entity_id) via LoggerAdapter extra dict.

SECURITY: Secrets, passwords, tokens, and API keys are redacted before
they reach the log stream.
"""

from __future__ import annotations

import logging
import re
import sys
from datetime import UTC
from typing import Any

# ── Patterns that must never appear in log output ────────────────

_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(password|passwd|secret|token|api[_-]?key|app[_-]?password|authorization)", re.I),
]

_REDACTION_VALUE = "***REDACTED***"


def _redact_value(value: str) -> str:
    """Replace values that look like secrets."""
    if len(value) > 6:
        return _REDACTION_VALUE
    return value


def _redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive keys in a dict."""
    clean: dict[str, Any] = {}
    for key, val in data.items():
        if any(p.search(key) for p in _SENSITIVE_PATTERNS):
            clean[key] = _REDACTION_VALUE
        elif isinstance(val, dict):
            clean[key] = _redact_dict(val)
        elif isinstance(val, str) and any(p.search(key) for p in _SENSITIVE_PATTERNS):
            clean[key] = _REDACTION_VALUE
        else:
            clean[key] = val
    return clean


# ── Custom Formatter ─────────────────────────────────────────────


class ZohraFormatter(logging.Formatter):
    """
    Structured formatter that includes contextual fields and redacts secrets.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Attach context fields if present
        for field in (
            "request_id",
            "job_id",
            "agent_run_id",
            "entity_id",
            "component",
            "operation",
        ):
            if not hasattr(record, field):
                setattr(record, field, None)

        # Redact message content
        msg = record.getMessage()
        for pattern in _SENSITIVE_PATTERNS:
            msg = pattern.sub(lambda m: _REDACTION_VALUE, msg)
        record.msg = msg
        record.args = None  # prevent double-format

        return super().format(record)


class ZohraJsonFormatter(logging.Formatter):
    """JSON-structured log output for production."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": "zohra-publisher",
            "component": getattr(record, "component", None),
            "operation": getattr(record, "operation", None),
            "request_id": getattr(record, "request_id", None),
            "job_id": getattr(record, "job_id", None),
            "agent_run_id": getattr(record, "agent_run_id", None),
            "entity_id": getattr(record, "entity_id", None),
            "message": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception_type"] = type(record.exc_info[1]).__name__
            log_entry["exception_message"] = str(record.exc_info[1])
            # Stack traces only in logs, never in API responses
            log_entry["stack_trace"] = self.formatException(record.exc_info)

        # Redact sensitive keys
        log_entry = _redact_dict(log_entry)

        return json.dumps(log_entry, default=str)


# ── Setup ────────────────────────────────────────────────────────


def setup_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """Configure application-wide logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if environment == "production":
        handler.setFormatter(ZohraJsonFormatter())
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)-25s | req=%(request_id)s | %(message)s"
        handler.setFormatter(ZohraFormatter(fmt, datefmt="%H:%M:%S"))

    root_logger.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "celery.worker", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str, **ctx: Any) -> logging.LoggerAdapter:
    """
    Return a LoggerAdapter with optional context fields.
    Usage:
        logger = get_logger(__name__, component="discovery")
        logger.info("Found 12 new sources", extra={"operation": "scan_rss"})
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, extra=ctx)
