from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest

from tests.support import test_user_registry

AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8001")
INVENTORY_BASE_URL = os.getenv("INVENTORY_BASE_URL", "http://localhost:8002")
TRANSACTION_BASE_URL = os.getenv("TRANSACTION_BASE_URL", "http://localhost:8003")
PRODUCTS_PATH = os.getenv("PRODUCTS_PATH", "/products")
PRODUCT_ID_FIELD = os.getenv("PRODUCT_ID_FIELD", "id")
OWNER_FIELD = os.getenv("PRODUCT_OWNER_FIELD", "seller_id")
CREATE_OWNER_FIELD = os.getenv("PRODUCT_CREATE_OWNER_FIELD", "seller_id")

_CONNECT_ERRORS = (httpx.ConnectError, httpx.TimeoutException, httpx.TransportError)


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def user_credentials(prefix: str) -> tuple[str, str]:
    suffix = uuid4().hex[:8]
    return f"{prefix}_{suffix}@example.com", "StrongPass123!"


def create_and_login_user(client: httpx.Client, prefix: str) -> dict:
    email, password = user_credentials(prefix)
    test_user_registry.register(email)

    try:
        register_response = client.post(
            f"{AUTH_BASE_URL}/auth/register",
            json={"email": email, "password": password},
        )
        assert register_response.status_code == 200, (
            f"Register failed [{register_response.status_code}]: {register_response.text}"
        )

        login_response = client.post(
            f"{AUTH_BASE_URL}/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200, (
            f"Login failed [{login_response.status_code}]: {login_response.text}"
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Auth service unreachable at {AUTH_BASE_URL}: {exc}")

    token = login_response.json()["access_token"]
    return {"email": email, "token": token}


def safe_request(client: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:
    try:
        return client.request(method, url, **kwargs)
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Service unreachable at {url}: {exc}")
