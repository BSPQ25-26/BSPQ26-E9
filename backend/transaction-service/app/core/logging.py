"""
Structured JSON logging via structlog (Sprint 3).
"""
from __future__ import annotations

import logging
import sys
import time
from typing import Any

import structlog

_CONFIGURED = False


def _service_name_processor(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict.setdefault("service", "transaction-service")
    return event_dict


def configure_logging() -> None:
    """Idempotent setup: JSON logs on stdout, INFO level."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            _service_name_processor,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name: str) -> Any:
    """Return a structlog bound logger (call configure_logging() once at app startup)."""
    return structlog.get_logger(name)


def log_request(logger: Any, endpoint: str, user_id: str, **kwargs: Any) -> None:
    """Log incoming request with sanitized context (no secrets)."""
    logger.info("http_request", endpoint=endpoint, user_id=str(user_id), **kwargs)


def log_result(logger: Any, endpoint: str, user_id: str, *, t0: float | None = None, **kwargs: Any) -> None:
    """Log successful handler completion; include duration_ms when t0 is set."""
    payload: dict[str, Any] = dict(kwargs)
    if t0 is not None:
        payload["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    logger.info("http_success", endpoint=endpoint, user_id=str(user_id), **payload)


def log_error(
    logger: Any,
    endpoint: str,
    user_id: str,
    *,
    error: str,
    t0: float | None = None,
    **kwargs: Any,
) -> None:
    """Log handler error; include duration_ms when t0 is set."""
    payload: dict[str, Any] = {"error": error, **kwargs}
    if t0 is not None:
        payload["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    logger.error("http_error", endpoint=endpoint, user_id=str(user_id), **payload)
