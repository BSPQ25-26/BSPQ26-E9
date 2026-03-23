import os
from uuid import uuid4

import httpx
import pytest

# $env:RUN_PRODUCT_INTEGRATION="1"; python.exe -m pytest tests/integration/test_protected_endpoints_integration.py -q -v

RUN_INTEGRATION = os.getenv("RUN_PRODUCT_INTEGRATION") == "1"
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8001")
INVENTORY_BASE_URL = os.getenv("INVENTORY_BASE_URL", "http://localhost:8002")
PRODUCTS_PATH = os.getenv("PRODUCTS_PATH", "/api/v1/products")
PRODUCT_ID_FIELD = os.getenv("PRODUCT_ID_FIELD", "id")

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_PRODUCT_INTEGRATION=1 to run protected endpoint integration tests.",
)

_CONNECT_ERRORS = (httpx.ConnectError, httpx.TimeoutException, httpx.TransportError)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _user_credentials(prefix: str) -> tuple[str, str]:
    suffix = uuid4().hex[:8]
    return f"{prefix}_{suffix}@example.com", "StrongPass123!"


def _create_and_login_user(client: httpx.Client, prefix: str) -> dict:
    email, password = _user_credentials(prefix)

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


def _create_product(client: httpx.Client, owner_token: str) -> dict:
    payload = {
        "title": f"protected-{uuid4().hex[:6]}",
        "description": "protected endpoint test item",
        "price": 100.0,
        "category": "electronics",
        "condition": "new",
    }

    try:
        response = client.post(
            f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}",
            json=payload,
            headers=_headers(owner_token),
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Inventory service unreachable at {INVENTORY_BASE_URL}: {exc}")

    if response.status_code == 404:
        pytest.skip(f"POST {PRODUCTS_PATH} not implemented yet in inventory-service")

    assert response.status_code in (200, 201), (
        f"Create product failed [{response.status_code}]: {response.text}"
    )
    data = response.json()
    assert PRODUCT_ID_FIELD in data, f"Response missing '{PRODUCT_ID_FIELD}': {data}"
    return data


def _request_by_method(
    client: httpx.Client,
    method: str,
    url: str,
    token: str | None = None,
    json: dict | None = None,
) -> httpx.Response:
    headers = _headers(token) if token else None

    try:
        if method == "GET":
            return client.get(url, headers=headers)
        if method == "PUT":
            return client.put(url, json=json or {"price": 120}, headers=headers)
        if method == "DELETE":
            return client.delete(url, headers=headers)
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Inventory service unreachable at {INVENTORY_BASE_URL}: {exc}")

    raise ValueError(f"Unsupported method: {method}")


@pytest.fixture()
def api_client():
    with httpx.Client(timeout=20.0) as client:
        yield client


@pytest.fixture()
def owner(api_client):
    try:
        return _create_and_login_user(api_client, "owner-private")
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Auth service unreachable: {exc}")


@pytest.fixture()
def outsider(api_client):
    try:
        return _create_and_login_user(api_client, "outsider-private")
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Auth service unreachable: {exc}")


@pytest.fixture()
def owned_product(api_client, owner):
    return _create_product(api_client, owner["token"])


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_private_product_endpoints_require_token_and_enforce_ownership(
    api_client,
    owner,
    outsider,
    owned_product,
    method,
):
    product_id = owned_product[PRODUCT_ID_FIELD]
    url = f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}/{product_id}"

    without_token = _request_by_method(api_client, method, url)
    assert without_token.status_code == 401, (
        f"{method} without token should be 401: {without_token.text}"
    )

    unauthorized_user = _request_by_method(api_client, method, url, token=outsider["token"])
    assert unauthorized_user.status_code == 403, (
        f"{method} with outsider token should be 403: {unauthorized_user.text}"
    )
