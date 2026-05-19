from __future__ import annotations

import threading

_lock = threading.Lock()
_emails: set[str] = set()


def register(email: str) -> None:
    cleaned = email.strip()
    if not cleaned:
        return
    with _lock:
        _emails.add(cleaned)


def snapshot() -> list[str]:
    with _lock:
        return sorted(_emails)


def clear() -> None:
    with _lock:
        _emails.clear()
