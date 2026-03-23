import os
from uuid import uuid4

import httpx
import pytest

# Start services:
# docker compose up --build

# Run with integration flag:
# cd backend/auth-service
# uvicorn app.main:app --port 8001 --reload
# $env:RUN_PRODUCT_INTEGRATION="1"; python.exe -m pytest tests/integration/test_product_crud_integration.py -q -v

RUN_INTEGRATION = os.getenv("RUN_PRODUCT_INTEGRATION") == "1"
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8001")
INVENTORY_BASE_URL = os.getenv("INVENTORY_BASE_URL", "http://localhost:8002")
PRODUCTS_PATH = os.getenv("PRODUCTS_PATH", "/api/v1/products")
PRODUCT_ID_FIELD = os.getenv("PRODUCT_ID_FIELD", "id")
OWNER_FIELD = os.getenv("PRODUCT_OWNER_FIELD", "seller_id")
CREATE_OWNER_FIELD = os.getenv("PRODUCT_CREATE_OWNER_FIELD", "seller_id")

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_PRODUCT_INTEGRATION=1 to run product integration tests.",
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


def _create_product(client: httpx.Client, owner_token: str, payload: dict | None = None) -> dict:
    base_payload = {
        "name": f"product-{uuid4().hex[:6]}",
        "description": "integration test item",
        "price": 100,
        "stock": 3,
    }
    if payload:
        base_payload.update(payload)

    try:
        response = client.post(
            f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}",
            json=base_payload,
            headers=_headers(owner_token),
        )
        assert response.status_code in (200, 201), (
            f"Create product failed [{response.status_code}]: {response.text}"
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Inventory service unreachable at {INVENTORY_BASE_URL}: {exc}")

    data = response.json()
    assert PRODUCT_ID_FIELD in data, f"Response missing '{PRODUCT_ID_FIELD}': {data}"
    return data


def _safe_request(client: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:
    try:
        return client.request(method, url, **kwargs)
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Service unreachable at {url}: {exc}")


@pytest.fixture()
def api_client():
    with httpx.Client(timeout=20.0) as client:
        yield client


@pytest.fixture()
def owner(api_client):
    try:
        return _create_and_login_user(api_client, "owner")
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Auth service unreachable: {exc}")


@pytest.fixture()
def outsider(api_client):
    try:
        return _create_and_login_user(api_client, "outsider")
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Auth service unreachable: {exc}")


def test_product_lifecycle_create_retrieve_update_delete_with_ownership(api_client, owner, outsider):
    created = _create_product(api_client, owner["token"])
    product_id = created[PRODUCT_ID_FIELD]
    url = f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}/{product_id}"

    # Retrieve: owner can read, non-owner is forbidden.
    owner_get = _safe_request(api_client, "GET", url, headers=_headers(owner["token"]))
    assert owner_get.status_code == 200, f"Owner GET failed: {owner_get.text}"

    outsider_get = _safe_request(api_client, "GET", url, headers=_headers(outsider["token"]))
    assert outsider_get.status_code == 403, f"Outsider GET should be 403: {outsider_get.text}"

    # Update: owner can update, non-owner is forbidden.
    owner_update = _safe_request(
        api_client, "PUT", url,
        json={"price": 120, "stock": 2},
        headers=_headers(owner["token"]),
    )
    assert owner_update.status_code in (200, 204), f"Owner PUT failed: {owner_update.text}"

    outsider_update = _safe_request(
        api_client, "PUT", url,
        json={"price": 140},
        headers=_headers(outsider["token"]),
    )
    assert outsider_update.status_code == 403, f"Outsider PUT should be 403: {outsider_update.text}"

    # Delete: non-owner first, then owner.
    outsider_delete = _safe_request(api_client, "DELETE", url, headers=_headers(outsider["token"]))
    assert outsider_delete.status_code == 403, f"Outsider DELETE should be 403: {outsider_delete.text}"

    owner_delete = _safe_request(api_client, "DELETE", url, headers=_headers(owner["token"]))
    assert owner_delete.status_code in (200, 204), f"Owner DELETE failed: {owner_delete.text}"


def test_create_rejects_owner_spoofing_when_owner_field_is_client_settable(api_client, owner, outsider):
    created = _create_product(api_client, owner["token"])

    if OWNER_FIELD not in created:
        pytest.skip(f"Cannot run spoof test: '{OWNER_FIELD}' not in product response.")

    spoof_payload = {
        CREATE_OWNER_FIELD: created[OWNER_FIELD],  # attempt to use owner's seller_id
        "name": f"spoof-{uuid4().hex[:6]}",
        "description": "spoof attempt",
        "price": 50,
        "stock": 1,
    }

    spoof_response = _safe_request(
        api_client, "POST",
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}",
        json=spoof_payload,
        headers=_headers(outsider["token"]),
    )
    # Server must ignore seller_id from body and assign it from the JWT instead
    assert spoof_response.status_code == 201, f"Expected 201, got: {spoof_response.text}"
    data = spoof_response.json()
    assert data[OWNER_FIELD] != created[OWNER_FIELD], \
        "seller_id must not be the spoofed owner's id"
    assert data[OWNER_FIELD] == outsider["email"], \
        "seller_id must match the authenticated user from the JWT, not the spoofed value"
