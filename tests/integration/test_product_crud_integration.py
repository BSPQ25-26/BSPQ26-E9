import os
from uuid import uuid4

import httpx
import pytest

from tests.support.integration_helpers import (
    AUTH_BASE_URL,
    CREATE_OWNER_FIELD,
    INVENTORY_BASE_URL,
    OWNER_FIELD,
    PRODUCTS_PATH,
    PRODUCT_ID_FIELD,
    _CONNECT_ERRORS,
    create_and_login_user,
    headers as _headers,
    safe_request as _safe_request,
)

# Start services:
# docker compose up --build

# Run with integration flag:
# cd backend/auth-service
# uvicorn app.main:app --port 8001 --reload
# $env:RUN_PRODUCT_INTEGRATION="1"; python.exe -m pytest tests/integration/test_product_crud_integration.py -q -v

RUN_INTEGRATION = os.getenv("RUN_PRODUCT_INTEGRATION") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_PRODUCT_INTEGRATION=1 to run product integration tests.",
)

def _create_product(client: httpx.Client, owner_token: str, payload: dict | None = None) -> dict:
    base_payload = {
        "name": f"product-{uuid4().hex[:6]}",
        "description": "integration test item",
        "category": "general",
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


@pytest.fixture()
def api_client():
    with httpx.Client(timeout=20.0) as client:
        yield client


@pytest.fixture()
def owner(api_client):
    return create_and_login_user(api_client, "owner")


@pytest.fixture()
def outsider(api_client):
    return create_and_login_user(api_client, "outsider")


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
        "category": "general",
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
