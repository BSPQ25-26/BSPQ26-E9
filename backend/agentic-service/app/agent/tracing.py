"""Shared LangSmith tracing utilities for all Wallabot agents."""

import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Latency thresholds — alert when a full agent call (all retries included) exceeds these.
CATEGORY_LATENCY_THRESHOLD_S: float = 15.0
PRICE_LATENCY_THRESHOLD_S: float = 30.0

try:
    from langsmith import Client as LangSmithClient
except ImportError:  # pragma: no cover - langsmith is bundled via langchain in production
    LangSmithClient = None  # type: ignore[assignment,misc]

_client: Any | None = None
_client_lock = threading.Lock()


def is_tracing_enabled() -> bool:
    return (
        os.getenv("LANGSMITH_TRACING", "").lower() == "true"
        or os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    )


def get_project_name() -> str:
    return (
        os.getenv("LANGCHAIN_PROJECT")
        or os.getenv("LANGSMITH_PROJECT")
        or "wallabot"
    )


def get_client() -> Any | None:
    global _client
    if not is_tracing_enabled() or LangSmithClient is None:
        return None
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
                api_url = os.getenv("LANGSMITH_ENDPOINT")
                _client = LangSmithClient(api_key=api_key, api_url=api_url)
    return _client


def log_validation_failure(
    component: str,
    title: str,
    attempt: int,
    error: Exception,
    extra_inputs: dict | None = None,
) -> None:
    """Log a Pydantic/parser validation failure to LangSmith as a tool run."""
    client = get_client()
    if client is None:
        return

    inputs: dict[str, Any] = {
        "title": title,
        "attempt": attempt,
        "max_attempts": 3,
        "event": "validation_failure",
    }
    if extra_inputs:
        inputs.update(extra_inputs)

    try:
        client.create_run(
            project_name=get_project_name(),
            name=f"wallabot_{component}_validation_failure",
            run_type="tool",
            inputs=inputs,
            error=f"{error.__class__.__name__}: {error}",
            extra={
                "metadata": {
                    "service": "agentic-service",
                    "component": component,
                    "error_type": error.__class__.__name__,
                }
            },
        )
    except Exception as telemetry_exc:  # noqa: BLE001 - telemetry must never break requests
        logger.warning(
            "Wallabot %s could not emit LangSmith validation event title=%r error_type=%s telemetry_error_type=%s",
            component,
            title,
            error.__class__.__name__,
            telemetry_exc.__class__.__name__,
        )


def log_latency_exceeded(
    component: str,
    title: str,
    elapsed_s: float,
    threshold_s: float,
) -> None:
    """Log a latency threshold violation — locally and to LangSmith when tracing is on."""
    logger.warning(
        "Wallabot %s latency threshold exceeded title=%r elapsed=%.2fs threshold=%.2fs",
        component,
        title,
        elapsed_s,
        threshold_s,
    )

    client = get_client()
    if client is None:
        return

    try:
        client.create_run(
            project_name=get_project_name(),
            name=f"wallabot_{component}_latency_exceeded",
            run_type="tool",
            inputs={"title": title, "component": component, "event": "latency_exceeded"},
            outputs={"elapsed_seconds": round(elapsed_s, 3), "threshold_seconds": threshold_s},
            extra={
                "metadata": {
                    "service": "agentic-service",
                    "component": component,
                    "elapsed_seconds": round(elapsed_s, 3),
                    "threshold_seconds": threshold_s,
                }
            },
        )
    except Exception as telemetry_exc:  # noqa: BLE001 - telemetry must never break requests
        logger.warning(
            "Wallabot %s could not emit LangSmith latency event title=%r telemetry_error_type=%s",
            component,
            title,
            telemetry_exc.__class__.__name__,
        )
