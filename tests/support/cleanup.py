from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

logger = logging.getLogger(__name__)

DEFAULT_SECRET = "dev-test-cleanup"
CLEANUP_PATH = "/internal/test/cleanup"


def is_auto_cleanup_enabled() -> bool:
    return os.getenv("TEST_AUTO_CLEANUP", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _cleanup_secret() -> str:
    return os.getenv("TEST_CLEANUP_SECRET", DEFAULT_SECRET)


def _cleanup_headers() -> dict[str, str]:
    return {"X-Test-Cleanup-Secret": _cleanup_secret()}


def _post_cleanup(
    client: httpx.Client,
    *,
    base_url: str,
    emails: list[str],
    run_id: str | None,
    purge_test_patterns: bool,
) -> dict:
    response = client.post(
        f"{base_url.rstrip('/')}{CLEANUP_PATH}",
        json={
            "emails": emails,
            "run_id": run_id,
            "purge_test_patterns": purge_test_patterns,
        },
        headers=_cleanup_headers(),
        timeout=30.0,
    )
    if response.status_code == 404:
        return {"skipped": True, "reason": "cleanup_disabled"}
    response.raise_for_status()
    return response.json()


def cleanup_test_users(
    *,
    emails: list[str] | None = None,
    run_id: str | None = None,
    auth_base_url: str | None = None,
    transaction_base_url: str | None = None,
    inventory_base_url: str | None = None,
    purge_test_patterns: bool = True,
) -> dict:
    if not is_auto_cleanup_enabled():
        return {"skipped": True, "reason": "TEST_AUTO_CLEANUP disabled"}

    resolved_emails = emails or []
    auth_url = auth_base_url or os.getenv("AUTH_BASE_URL", "http://localhost:8001")
    transaction_url = transaction_base_url or os.getenv(
        "TRANSACTION_BASE_URL",
        "http://localhost:8003",
    )
    inventory_url = inventory_base_url or os.getenv(
        "INVENTORY_BASE_URL",
        "http://localhost:8002",
    )

    targets = [
        ("auth", auth_url),
        ("transaction", transaction_url),
        ("inventory", inventory_url),
    ]

    results: dict[str, dict] = {}
    with httpx.Client() as client, ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(
                _post_cleanup,
                client,
                base_url=base_url,
                emails=resolved_emails,
                run_id=run_id,
                purge_test_patterns=purge_test_patterns,
            ): name
            for name, base_url in targets
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                logger.warning("Test cleanup failed for %s: %s", name, exc)
                results[name] = {"error": str(exc)}

    return results
