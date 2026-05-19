from __future__ import annotations

import logging
import os

import pytest

from tests.support import cleanup, test_user_registry

logger = logging.getLogger(__name__)


def _integration_enabled() -> bool:
    return any(
        os.getenv(flag) == "1"
        for flag in (
            "RUN_PRODUCT_INTEGRATION",
            "RUN_PURCHASE_FLOW_INTEGRATION",
            "RUN_STATE_MACHINE_INTEGRATION",
        )
    )


def pytest_sessionfinish(session, exitstatus) -> None:
    if not _integration_enabled():
        return

    emails = test_user_registry.snapshot()
    if not emails and not cleanup.is_auto_cleanup_enabled():
        return

    try:
        results = cleanup.cleanup_test_users(
            emails=emails,
            run_id=os.getenv("PERF_RUN_ID"),
            purge_test_patterns=True,
        )
        logger.info("Integration test cleanup results: %s", results)
    except Exception:
        logger.exception("Integration test cleanup failed")
    finally:
        test_user_registry.clear()
