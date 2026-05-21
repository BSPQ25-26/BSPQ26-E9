"""Sprint 3 acceptance runner for the running Wallabot Docker stack.

This script exercises the new features with realistic black-box data:
- authentication and purchase flow for ratings/public profile
- catalog filters and keyword search
- Wallabot category suggestion and optional live pricing

Run it against the Docker Compose stack after the services are healthy.
python tests/E2E/scenario_test.py

Creates seller-/buyer- test users and removes them plus related inventory and
transaction data at the end (even if a scenario fails). Requires
ENABLE_TEST_CLEANUP=true and TEST_CLEANUP_SECRET matching the stack (Compose defaults).
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger("mini_wallapop.e2e")

from tests.support.cleanup import cleanup_test_users


AUTH_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
INVENTORY_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8002")
TRANSACTION_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://localhost:8003")
WALLABOT_URL = os.getenv("WALLABOT_SERVICE_URL", "http://localhost:8004")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

RUN_WALLABOT_PRICE = os.getenv("RUN_WALLABOT_PRICE", "0") == "1"
REQUEST_TIMEOUT = float(os.getenv("ACCEPTANCE_TIMEOUT_SECONDS", "20"))


@dataclass(slots=True)
class DemoUsers:
    seller_email: str
    buyer_email: str
    password: str
    seller_token: str
    buyer_token: str


def _request(method: str, url: str, **kwargs: Any) -> requests.Response:
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    response = requests.request(method, url, **kwargs)
    return response


def _assert_ok(response: requests.Response, expected_status: int | None = None) -> None:
    if expected_status is not None:
        assert response.status_code == expected_status, response.text
        return

    assert response.ok, f"{response.status_code}: {response.text}"


def _register_and_login(email: str, password: str) -> str:
    _request(
        "post",
        f"{AUTH_URL}/auth/register",
        json={"email": email, "password": password},
    )

    login_response = _request(
        "post",
        f"{AUTH_URL}/auth/login",
        json={"email": email, "password": password},
    )
    _assert_ok(login_response)

    token = login_response.json().get("access_token")
    assert token, login_response.text
    return token


def _resolve_user_id_by_email(email: str) -> int:
    query_code = (
        "import os, sys; "
        "from sqlalchemy import create_engine, text; "
        "engine = create_engine(os.getenv('AUTH_DATABASE_URL')); "
        "conn = engine.connect(); "
        "row = conn.execute(text('SELECT id FROM users WHERE email = :email'), {'email': sys.argv[1]}).fetchone(); "
        "conn.close(); "
        "print(row[0] if row else '')"
    )

    commands = [
        ["docker", "compose", "exec", "-T", "auth-service", "python", "-c", query_code, email],
        ["docker-compose", "exec", "-T", "auth-service", "python", "-c", query_code, email],
    ]

    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

        value = result.stdout.strip()
        if value.isdigit():
            return int(value)

    raise AssertionError(f"Could not resolve user id for {email}")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_demo_users() -> DemoUsers:
    ts = int(time.time())
    seller_email = f"seller-{ts}@example.com"
    buyer_email = f"buyer-{ts}@example.com"
    password = "pass1234"

    seller_token = _register_and_login(seller_email, password)
    buyer_token = _register_and_login(buyer_email, password)

    return DemoUsers(
        seller_email=seller_email,
        buyer_email=buyer_email,
        password=password,
        seller_token=seller_token,
        buyer_token=buyer_token,
    )


def _create_inventory_product(token: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = _request(
        "post",
        f"{INVENTORY_URL}/api/v1/products",
        json=payload,
        headers=_auth_headers(token),
    )
    _assert_ok(response, 201)
    return response.json()


def _create_transaction_product(token: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = _request(
        "post",
        f"{TRANSACTION_URL}/products/",
        json=payload,
        headers=_auth_headers(token),
    )
    _assert_ok(response, 201)
    return response.json()


def _top_up_wallet(token: str, amount: float) -> dict[str, Any]:
    response = _request(
        "post",
        f"{TRANSACTION_URL}/wallet/topup",
        json={"amount": amount},
        headers=_auth_headers(token),
    )
    _assert_ok(response)
    return response.json()


def _buy_transaction_product(token: str, product_id: int) -> dict[str, Any]:
    reserve_response = _request(
        "post",
        f"{TRANSACTION_URL}/products/{product_id}/reserve",
        headers=_auth_headers(token),
    )
    _assert_ok(reserve_response)

    buy_response = _request(
        "post",
        f"{TRANSACTION_URL}/products/{product_id}/buy",
        headers=_auth_headers(token),
    )
    _assert_ok(buy_response)
    return buy_response.json()


def _create_rating(token: str, seller_id: int, transaction_id: int) -> dict[str, Any]:
    response = _request(
        "post",
        f"{AUTH_URL}/ratings",
        json={
            "to_user_id": seller_id,
            "transaction_id": transaction_id,
            "stars": 5,
            "review_text": "Exactly as described. Fast delivery and great communication.",
        },
        headers=_auth_headers(token),
    )
    _assert_ok(response)
    return response.json()


def _run_profile_and_ratings_scenario(users: DemoUsers) -> dict[str, Any]:
    product = _create_transaction_product(
        users.seller_token,
        {
            "title": "Used iPhone 13 Pro 128GB",
            "description": "Graphite phone in excellent shape with charging cable and box.",
            "category": "electronics",
            "price": 649.0,
        },
    )

    _top_up_wallet(users.buyer_token, 700.0)
    buy_result = _buy_transaction_product(users.buyer_token, product["id"])
    transaction_id = buy_result.get("transaction_id") or buy_result.get("id")
    assert transaction_id, buy_result

    seller_id = _resolve_user_id_by_email(users.seller_email)
    rating = _create_rating(users.buyer_token, seller_id, int(transaction_id))

    profile_response = _request("get", f"{AUTH_URL}/users/{seller_id}/profile")
    _assert_ok(profile_response)
    profile = profile_response.json()
    assert profile["username"] == users.seller_email
    assert profile["avg_rating"] is not None, profile

    ratings_response = _request(
        "get",
        f"{AUTH_URL}/users/{seller_id}/ratings",
        params={"skip": 0, "limit": 10},
    )
    _assert_ok(ratings_response)
    ratings = ratings_response.json()
    assert ratings, ratings_response.text
    assert ratings[0]["reviewer_username"] == users.buyer_email

    return {
        "seller_id": seller_id,
        "transaction_id": int(transaction_id),
        "rating": rating,
        "profile": profile,
        "product": product,
    }


def _run_catalog_scenario(users: DemoUsers) -> dict[str, Any]:
    created_products = [
        _create_inventory_product(
            users.seller_token,
            {
                "title": "iPhone 13 Pro 128GB",
                "description": "Unlocked graphite phone, lightly used, original box included.",
                "category": "electronics",
                "price": 799.0,
                "condition": "Like New",
            },
        ),
        _create_inventory_product(
            users.seller_token,
            {
                "title": "Wooden Desk Lamp",
                "description": "Warm LED lamp for a home office desk.",
                "category": "home & garden",
                "price": 25.0,
                "condition": "Good",
            },
        ),
        _create_inventory_product(
            users.seller_token,
            {
                "title": "Vintage Camera Bag",
                "description": "Durable camera bag with padded inserts and shoulder strap.",
                "category": "collectibles & art",
                "price": 38.0,
                "condition": "Good",
            },
        ),
        _create_inventory_product(
            users.seller_token,
            {
                "title": "Paperback Novel Bundle",
                "description": "Three lightly read paperbacks in excellent condition.",
                "category": "books & media",
                "price": 12.0,
                "condition": "New",
            },
        ),
    ]

    catalog_response = _request(
        "get",
        f"{INVENTORY_URL}/api/v1/products",
        headers=_auth_headers(users.buyer_token),
        params={
            "category": "electronics",
            "condition": "Like New",
            "min_price": 700,
            "max_price": 900,
        },
    )
    _assert_ok(catalog_response)
    filtered_titles = {item["title"] for item in catalog_response.json()}
    assert filtered_titles == {"iPhone 13 Pro 128GB"}, filtered_titles

    search_response = _request(
        "get",
        f"{INVENTORY_URL}/api/v1/products",
        headers=_auth_headers(users.buyer_token),
        params={"q": "camera"},
    )
    _assert_ok(search_response)
    search_titles = {item["title"] for item in search_response.json()}
    assert search_titles == {"Vintage Camera Bag"}, search_titles

    combined_response = _request(
        "get",
        f"{INVENTORY_URL}/api/v1/products",
        headers=_auth_headers(users.buyer_token),
        params={"q": "lamp", "category": "home & garden", "condition": "Good"},
    )
    _assert_ok(combined_response)
    combined_titles = {item["title"] for item in combined_response.json()}
    assert combined_titles == {"Wooden Desk Lamp"}, combined_titles

    return {
        "created_products": created_products,
        "filtered_titles": filtered_titles,
        "search_titles": search_titles,
        "combined_titles": combined_titles,
    }


def _run_wallabot_scenario() -> dict[str, Any]:
    category_response = _request(
        "post",
        f"{WALLABOT_URL}/wallabot/category",
        json={
            "title": "Used iPhone 13 Pro 128GB",
            "description": "Unlocked graphite phone in excellent condition, box included.",
            "available_categories": [
                "Electronics",
                "Clothing & Accessories",
                "Home & Garden",
                "Sports & Outdoors",
                "Books & Media",
                "Other",
            ],
        },
    )
    _assert_ok(category_response)
    category_data = category_response.json()
    assert category_data.get("suggested_category"), category_data

    price_data: dict[str, Any] | None = None
    if RUN_WALLABOT_PRICE:
        price_response = _request(
            "post",
            f"{WALLABOT_URL}/wallabot/price",
            json={
                "title": "Used iPhone 13 Pro 128GB",
                "description": "Unlocked graphite phone in excellent condition, box included.",
                "condition": "Like New",
            },
        )
        _assert_ok(price_response)
        price_data = price_response.json()
        assert price_data["price_range_min"] <= price_data["recommended_price"] <= price_data["price_range_max"], price_data

    return {
        "category": category_data,
        "price": price_data,
        "price_enabled": RUN_WALLABOT_PRICE,
    }


def run_acceptance_suite() -> dict[str, Any]:
    logger.info("Running Sprint 3 acceptance scenarios against the Docker stack")
    logger.info("Frontend: %s", FRONTEND_URL)

    demo_users: DemoUsers | None = None
    try:
        demo_users = _seed_demo_users()
        profile_and_ratings = _run_profile_and_ratings_scenario(demo_users)
        catalog = _run_catalog_scenario(demo_users)
        wallabot = _run_wallabot_scenario()

        summary = {
            "profile_and_ratings": {
                "seller_email": demo_users.seller_email,
                "buyer_email": demo_users.buyer_email,
                "seller_id": profile_and_ratings["seller_id"],
                "transaction_id": profile_and_ratings["transaction_id"],
            },
            "catalog": catalog,
            "wallabot": wallabot,
            "frontend_routes_to_review": [
                f"{FRONTEND_URL}/#/products",
                f"{FRONTEND_URL}/#/products/create",
            ],
        }

        return summary
    finally:
        if demo_users is not None:
            results = cleanup_test_users(
                emails=[demo_users.seller_email, demo_users.buyer_email],
                auth_base_url=AUTH_URL,
                transaction_base_url=TRANSACTION_URL,
                inventory_base_url=INVENTORY_URL,
                purge_test_patterns=False,
            )
            logger.info("Cleanup (auth/inventory/transaction): %s", results)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    summary = run_acceptance_suite()
    logger.info("Acceptance summary")
    for key, value in summary.items():
        logger.info("- %s: %s", key, value)


if __name__ == "__main__":
    main()
