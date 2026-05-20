import os
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.rating import Rating
from app.models.social_account import SocialAccount
from app.models.user import User

PROTECTED_EMAILS = frozenset(
    {
        "alice@example.com",
        "bob@example.com",
        "charlie@example.com",
        "service@internal",
    }
)

INTEGRATION_EMAIL_RE = re.compile(r"^[\w-]+_[0-9a-f]{8}@example\.com$")
PERF_EMAIL_RE = re.compile(r"^perf-[0-9a-f]{8}-.+@example\.com$")
FRONTEND_IT_EMAIL_RE = re.compile(r"^frontend-it-\d+@example\.com$")
# tests/E2E/scenario_test.py — seller-<unix_ts>@ / buyer-<unix_ts>@
E2E_SCENARIO_EMAIL_RE = re.compile(r"^(seller|buyer)-\d+@example\.com$")


def _is_test_email(email: str) -> bool:
    if email in PROTECTED_EMAILS:
        return False
    return bool(
        INTEGRATION_EMAIL_RE.match(email)
        or PERF_EMAIL_RE.match(email)
        or FRONTEND_IT_EMAIL_RE.match(email)
        or E2E_SCENARIO_EMAIL_RE.match(email)
    )


def _collect_target_emails(
    db: Session,
    *,
    emails: list[str],
    run_id: str | None,
    purge_test_patterns: bool,
) -> set[str]:
    targets: set[str] = set()

    for email in emails:
        cleaned = email.strip()
        if cleaned and _is_test_email(cleaned):
            targets.add(cleaned)

    filters = []
    if run_id:
        filters.append(User.email.like(f"perf-{run_id}-%"))

    if purge_test_patterns:
        filters.append(User.email.like("frontend-it-%@example.com"))
        filters.append(User.email.like("perf-%"))
        filters.append(User.email.like("%@example.com"))

    if filters:
        for user in db.query(User).filter(or_(*filters)).all():
            if _is_test_email(user.email):
                targets.add(user.email)

    return targets


def cleanup_test_users(
    db: Session,
    *,
    emails: list[str],
    run_id: str | None,
    purge_test_patterns: bool,
) -> dict:
    target_emails = _collect_target_emails(
        db,
        emails=emails,
        run_id=run_id,
        purge_test_patterns=purge_test_patterns,
    )
    if not target_emails:
        return {"deleted_users": 0, "deleted_ratings": 0, "deleted_social_accounts": 0}

    users = db.query(User).filter(User.email.in_(target_emails)).all()
    user_ids = [user.id for user in users]
    if not user_ids:
        return {"deleted_users": 0, "deleted_ratings": 0, "deleted_social_accounts": 0}

    deleted_ratings = (
        db.query(Rating)
        .filter(
            or_(
                Rating.from_user_id.in_(user_ids),
                Rating.to_user_id.in_(user_ids),
            )
        )
        .delete(synchronize_session=False)
    )
    deleted_social = (
        db.query(SocialAccount)
        .filter(SocialAccount.user_id.in_(user_ids))
        .delete(synchronize_session=False)
    )
    deleted_users = (
        db.query(User)
        .filter(User.id.in_(user_ids))
        .delete(synchronize_session=False)
    )
    db.commit()

    return {
        "deleted_users": deleted_users,
        "deleted_ratings": deleted_ratings,
        "deleted_social_accounts": deleted_social,
    }


def is_test_cleanup_enabled() -> bool:
    return os.getenv("ENABLE_TEST_CLEANUP", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
