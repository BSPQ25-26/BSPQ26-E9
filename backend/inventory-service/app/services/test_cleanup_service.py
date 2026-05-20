import os
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.product import Product

INTEGRATION_EMAIL_RE = re.compile(r"^[\w-]+_[0-9a-f]{8}@example\.com$")
PERF_EMAIL_RE = re.compile(r"^perf-[0-9a-f]{8}-.+@example\.com$")
FRONTEND_IT_EMAIL_RE = re.compile(r"^frontend-it-\d+@example\.com$")
E2E_SCENARIO_EMAIL_RE = re.compile(r"^(seller|buyer)-\d+@example\.com$")


def _is_test_seller_id(seller_id: str) -> bool:
    return bool(
        INTEGRATION_EMAIL_RE.match(seller_id)
        or PERF_EMAIL_RE.match(seller_id)
        or FRONTEND_IT_EMAIL_RE.match(seller_id)
        or E2E_SCENARIO_EMAIL_RE.match(seller_id)
    )


def cleanup_test_data(
    db: Session,
    *,
    emails: list[str],
    run_id: str | None,
    purge_test_patterns: bool,
) -> dict:
    explicit_emails = {
        email.strip()
        for email in emails
        if email.strip() and _is_test_seller_id(email.strip())
    }

    filters = []
    if explicit_emails:
        filters.append(Product.seller_id.in_(explicit_emails))

    if run_id:
        filters.append(Product.seller_id.like(f"perf-{run_id}-%"))

    if purge_test_patterns:
        filters.extend(
            [
                Product.seller_id.like("frontend-it-%@example.com"),
                Product.seller_id.like("perf-%"),
                Product.seller_id.like("%@example.com"),
            ]
        )

    if not filters:
        return {"deleted_products": 0}

    query = db.query(Product).filter(or_(*filters))
    products = [product for product in query.all() if _is_test_seller_id(product.seller_id)]
    if not products:
        return {"deleted_products": 0}

    for product in products:
        db.delete(product)

    db.commit()
    return {"deleted_products": len(products)}


def is_test_cleanup_enabled() -> bool:
    return os.getenv("ENABLE_TEST_CLEANUP", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
