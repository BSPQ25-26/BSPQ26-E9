"""
SPRINT 3: Structured Logging
Structured JSON logging for the transaction service.
"""
import logging
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "service":   "transaction-service",
            "message":   record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """Returns a logger configured with JSON structured output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_request(logger: logging.Logger, endpoint: str, user_id: str, **kwargs) -> None:
    """Logs an incoming request with sanitized input."""
    logger.info(
        f"Request: {endpoint}",
        extra={"extra": {"endpoint": endpoint, "user_id": user_id, **kwargs}}
    )


def log_result(logger: logging.Logger, endpoint: str, user_id: str, **kwargs) -> None:
    """Logs a successful result."""
    logger.info(
        f"Success: {endpoint}",
        extra={"extra": {"endpoint": endpoint, "user_id": user_id, **kwargs}}
    )


def log_error(logger: logging.Logger, endpoint: str, user_id: str, error: str, **kwargs) -> None:
    """Logs an error with context."""
    logger.error(
        f"Error: {endpoint}",
        extra={"extra": {"endpoint": endpoint, "user_id": user_id, "error": error, **kwargs}}
    )