import os
from uuid import uuid4

import httpx
import pytest

#Start services:
#docker compose up --build
#Run with integration flag:
#RUN_PRODUCT_INTEGRATION=1 python.exe -m pytest test_product_crud_integration.py -q

RUN_INTEGRATION = os.getenv("RUN_PRODUCT_INTEGRATION") == "1"
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8001")
INVENTORY_BASE_URL = os.getenv("INVENTORY_BASE_URL", "http://localhost:8002")
PRODUCTS_PATH = os.getenv("PRODUCTS_PATH", "/products")
PRODUCT_ID_FIELD = os.getenv("PRODUCT_ID_FIELD", "id")
OWNER_FIELD = os.getenv("PRODUCT_OWNER_FIELD", "owner_id")
CREATE_OWNER_FIELD = os.getenv("PRODUCT_CREATE_OWNER_FIELD", "owner_id")

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_PRODUCT_INTEGRATION=1 to run product integration tests.",
)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _user_credentials(prefix: str) -> tuple[str, str]:
    suffix = uuid4().hex[:8]
    return f"{prefix}_{suffix}@example.com", "StrongPass123!"


def _create_and_login_user(client: httpx.Client, prefix: str) -> dict:
    email, password = _user_credentials(prefix)

    register_response = client.post(
        f"{AUTH_BASE_URL}/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200, register_response.text

    login_response = client.post(
        f"{AUTH_BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text

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

    response = client.post(
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}",
        json=base_payload,
        headers=_headers(owner_token),
    )

    assert response.status_code in (200, 201), response.text
    data = response.json()
    assert PRODUCT_ID_FIELD in data
    return data


@pytest.fixture()
def api_client():
    with httpx.Client(timeout=20.0) as client:
        yield client


@pytest.fixture()
def owner(api_client):
    return _create_and_login_user(api_client, "owner")


@pytest.fixture()
def outsider(api_client):
    return _create_and_login_user(api_client, "outsider")


def test_product_lifecycle_create_retrieve_update_delete_with_ownership(api_client, owner, outsider):
    created = _create_product(api_client, owner["token"])
    product_id = created[PRODUCT_ID_FIELD]

    # Retrieve: owner can read, non-owner is forbidden.
    owner_get = api_client.get(
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}/{product_id}",
        headers=_headers(owner["token"]),
    )
    assert owner_get.status_code == 200, owner_get.text

    outsider_get = api_client.get(
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}/{product_id}",
        headers=_headers(outsider["token"]),
    )
    assert outsider_get.status_code == 403, outsider_get.text

    # Update: owner can update, non-owner is forbidden.
    update_payload = {"price": 120, "stock": 2}
    owner_update = api_client.put(
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}/{product_id}",
        json=update_payload,
        headers=_headers(owner["token"]),
    )
    assert owner_update.status_code in (200, 204), owner_update.text

    outsider_update = api_client.put(
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}/{product_id}",
        json={"price": 140},
        headers=_headers(outsider["token"]),
    )
    assert outsider_update.status_code == 403, outsider_update.text

    # Delete: owner can delete, non-owner is forbidden.
    outsider_delete = api_client.delete(
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}/{product_id}",
        headers=_headers(outsider["token"]),
    )
    assert outsider_delete.status_code == 403, outsider_delete.text

    owner_delete = api_client.delete(
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}/{product_id}",
        headers=_headers(owner["token"]),
    )
    assert owner_delete.status_code in (200, 204), owner_delete.text


def test_create_rejects_owner_spoofing_when_owner_field_is_client_settable(api_client, owner, outsider):
    created = _create_product(api_client, owner["token"])

    if OWNER_FIELD not in created:
        pytest.skip(
            f"Cannot run create ownership spoof test because '{OWNER_FIELD}' is not in product response."
        )

    spoofed_owner_value = created[OWNER_FIELD]
    spoof_payload = {
        CREATE_OWNER_FIELD: spoofed_owner_value,
        "name": f"spoof-{uuid4().hex[:6]}",
        "description": "spoof attempt",
        "price": 50,
        "stock": 1,
    }

    spoof_response = api_client.post(
        f"{INVENTORY_BASE_URL}{PRODUCTS_PATH}",
        json=spoof_payload,
        headers=_headers(outsider["token"]),
    )

    assert spoof_response.status_code == 403, spoof_response.text
