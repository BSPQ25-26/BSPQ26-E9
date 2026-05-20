import os
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Product, ProductStateHistory, Transaction, WalletLedger

INTEGRATION_EMAIL_RE = re.compile(r"^[\w-]+_[0-9a-f]{8}@example\.com$")
PERF_EMAIL_RE = re.compile(r"^perf-[0-9a-f]{8}-.+@example\.com$")
FRONTEND_IT_EMAIL_RE = re.compile(r"^frontend-it-\d+@example\.com$")
E2E_SCENARIO_EMAIL_RE = re.compile(r"^(seller|buyer)-\d+@example\.com$")


def _is_test_user_id(user_id: str) -> bool:
    return bool(
        INTEGRATION_EMAIL_RE.match(user_id)
        or PERF_EMAIL_RE.match(user_id)
        or FRONTEND_IT_EMAIL_RE.match(user_id)
        or E2E_SCENARIO_EMAIL_RE.match(user_id)
    )


def _like_patterns(*, run_id: str | None, purge_test_patterns: bool) -> list[str]:
    patterns: list[str] = []
    if run_id:
        patterns.append(f"perf-{run_id}-%")
    if purge_test_patterns:
        patterns.extend(
            [
                "frontend-it-%@example.com",
                "perf-%",
                "%@example.com",
            ]
        )
    return patterns


def _add_matches_from_column(db: Session, column, patterns: list[str], targets: set[str]) -> None:
    for pattern in patterns:
        for (value,) in db.query(column).filter(column.like(pattern)).distinct():
            if value and _is_test_user_id(value):
                targets.add(value)


def _collect_target_user_ids(
    db: Session,
    *,
    emails: list[str],
    run_id: str | None,
    purge_test_patterns: bool,
) -> set[str]:
    targets: set[str] = set()

    for email in emails:
        cleaned = email.strip()
        if cleaned and _is_test_user_id(cleaned):
            targets.add(cleaned)

    patterns = _like_patterns(run_id=run_id, purge_test_patterns=purge_test_patterns)
    if patterns:
        _add_matches_from_column(db, Product.owner_id, patterns, targets)
        _add_matches_from_column(db, Product.reserved_by, patterns, targets)
        _add_matches_from_column(db, WalletLedger.user_id, patterns, targets)
        _add_matches_from_column(db, Transaction.buyer_id, patterns, targets)
        _add_matches_from_column(db, Transaction.seller_id, patterns, targets)

    return targets


def cleanup_test_data(
    db: Session,
    *,
    emails: list[str],
    run_id: str | None,
    purge_test_patterns: bool,
) -> dict:
    target_user_ids = _collect_target_user_ids(
        db,
        emails=emails,
        run_id=run_id,
        purge_test_patterns=purge_test_patterns,
    )
    if not target_user_ids:
        return {
            "deleted_products": 0,
            "deleted_state_history": 0,
            "deleted_transactions": 0,
            "deleted_wallet_entries": 0,
        }

    user_filter = or_(
        Product.owner_id.in_(target_user_ids),
        Product.reserved_by.in_(target_user_ids),
    )
    product_ids = [
        row[0] for row in db.query(Product.id).filter(user_filter).distinct().all()
    ]

    deleted_transactions = 0
    deleted_state_history = 0
    deleted_products = 0

    if product_ids:
        deleted_transactions = (
            db.query(Transaction)
            .filter(
                or_(
                    Transaction.product_id.in_(product_ids),
                    Transaction.buyer_id.in_(target_user_ids),
                    Transaction.seller_id.in_(target_user_ids),
                )
            )
            .delete(synchronize_session=False)
        )
        deleted_state_history = (
            db.query(ProductStateHistory)
            .filter(ProductStateHistory.product_id.in_(product_ids))
            .delete(synchronize_session=False)
        )
        deleted_products = (
            db.query(Product)
            .filter(Product.id.in_(product_ids))
            .delete(synchronize_session=False)
        )

    deleted_wallet_entries = (
        db.query(WalletLedger)
        .filter(WalletLedger.user_id.in_(target_user_ids))
        .delete(synchronize_session=False)
    )
    db.commit()

    return {
        "deleted_products": deleted_products,
        "deleted_state_history": deleted_state_history,
        "deleted_transactions": deleted_transactions,
        "deleted_wallet_entries": deleted_wallet_entries,
    }


def is_test_cleanup_enabled() -> bool:
    return os.getenv("ENABLE_TEST_CLEANUP", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
