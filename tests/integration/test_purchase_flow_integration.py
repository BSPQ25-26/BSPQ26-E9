import os
from uuid import uuid4

import httpx
import pytest


# Run with integration flag:
# $env:RUN_PURCHASE_FLOW_INTEGRATION="1"; python.exe -m pytest tests/integration/test_purchase_flow_integration.py -q -v

RUN_INTEGRATION = (
    os.getenv("RUN_PURCHASE_FLOW_INTEGRATION") == "1"
    or os.getenv("RUN_STATE_MACHINE_INTEGRATION") == "1"
)
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8001")
TRANSACTION_BASE_URL = os.getenv("TRANSACTION_BASE_URL", "http://localhost:8003")
PRODUCTS_PATH = os.getenv("PRODUCTS_PATH", "/products")
PRODUCT_ID_FIELD = os.getenv("PRODUCT_ID_FIELD", "id")

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_PURCHASE_FLOW_INTEGRATION=1 to run purchase flow integration tests.",
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

    return {"email": email, "token": login_response.json()["access_token"]}


def _create_product(client: httpx.Client, owner_token: str, price: float) -> dict:
    payload = {
        "title": f"purchase-flow-{uuid4().hex[:6]}",
        "description": "integration test product for purchase flow",
        "price": price,
        "category": "electronics",
    }

    try:
        response = client.post(
            f"{TRANSACTION_BASE_URL}{PRODUCTS_PATH}/",
            json=payload,
            headers=_headers(owner_token),
        )
        assert response.status_code in (200, 201), (
            f"Create product failed [{response.status_code}]: {response.text}"
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable at {TRANSACTION_BASE_URL}: {exc}")

    data = response.json()
    assert PRODUCT_ID_FIELD in data, f"Response missing '{PRODUCT_ID_FIELD}': {data}"
    return data


def _top_up_wallet(client: httpx.Client, token: str, amount: float) -> dict:
    try:
        response = client.post(
            f"{TRANSACTION_BASE_URL}/wallet/topup",
            json={"amount": amount},
            headers=_headers(token),
        )
        assert response.status_code == 200, (
            f"Top-up failed [{response.status_code}]: {response.text}"
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable at {TRANSACTION_BASE_URL}: {exc}")

    return response.json()


def _reserve_product(client: httpx.Client, product_id: int, token: str) -> dict:
    try:
        response = client.post(
            f"{TRANSACTION_BASE_URL}{PRODUCTS_PATH}/{product_id}/reserve",
            headers=_headers(token),
        )
        assert response.status_code == 200, (
            f"Reserve failed [{response.status_code}]: {response.text}"
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable at {TRANSACTION_BASE_URL}: {exc}")

    return response.json()


def _buy_product(client: httpx.Client, product_id: int, token: str) -> httpx.Response:
    try:
        return client.post(
            f"{TRANSACTION_BASE_URL}{PRODUCTS_PATH}/{product_id}/buy",
            headers=_headers(token),
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable at {TRANSACTION_BASE_URL}: {exc}")


def _get_wallet_history(client: httpx.Client, token: str) -> dict:
    try:
        response = client.get(
            f"{TRANSACTION_BASE_URL}/wallet/history",
            headers=_headers(token),
        )
        assert response.status_code == 200, (
            f"Wallet history failed [{response.status_code}]: {response.text}"
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable at {TRANSACTION_BASE_URL}: {exc}")

    return response.json()


def _get_product_history(client: httpx.Client, product_id: int, token: str) -> list[dict]:
    try:
        response = client.get(
            f"{TRANSACTION_BASE_URL}{PRODUCTS_PATH}/{product_id}/history",
            headers=_headers(token),
        )
        assert response.status_code == 200, (
            f"Product history failed [{response.status_code}]: {response.text}"
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable at {TRANSACTION_BASE_URL}: {exc}")

    return response.json()


@pytest.fixture()
def api_client():
    with httpx.Client(timeout=20.0) as client:
        yield client


@pytest.fixture()
def seller(api_client):
    return _create_and_login_user(api_client, "seller-purchase")


@pytest.fixture()
def buyer(api_client):
    return _create_and_login_user(api_client, "buyer-purchase")


def test_full_purchase_flow_records_reservation_purchase_and_wallet_ledger_entries(
    api_client,
    seller,
    buyer,
):
    product = _create_product(api_client, seller["token"], price=125.0)
    product_id = product[PRODUCT_ID_FIELD]

    top_up = _top_up_wallet(api_client, buyer["token"], amount=250.0)
    assert top_up["balance"] == 250.0

    reservation = _reserve_product(api_client, product_id, buyer["token"])
    assert reservation["product_id"] == product_id
    assert reservation["state"] == "reserved"
    assert reservation["reserved_by"] == buyer["email"]

    purchase_response = _buy_product(api_client, product_id, buyer["token"])
    assert purchase_response.status_code == 201, purchase_response.text

    purchase = purchase_response.json()
    assert purchase["buyer_id"] == buyer["email"]
    assert purchase["seller_id"] == seller["email"]
    assert purchase["product_id"] == product_id
    assert purchase["amount"] == 125.0
    assert purchase["status"] == "completed"
    assert purchase["completed_at"] is not None

    buyer_history = _get_wallet_history(api_client, buyer["token"])
    assert buyer_history["total"] == 2
    assert buyer_history["balance"] == 125.0
    assert len(buyer_history["entries"]) == 2

    buyer_latest = buyer_history["entries"][0]
    buyer_earlier = buyer_history["entries"][1]
    assert buyer_latest["transaction_type"] == "PURCHASE"
    assert buyer_latest["amount"] == -125.0
    assert buyer_latest["balance_after"] == 125.0
    assert buyer_earlier["transaction_type"] == "TOP_UP"
    assert buyer_earlier["amount"] == 250.0
    assert buyer_earlier["balance_after"] == 250.0

    seller_history = _get_wallet_history(api_client, seller["token"])
    assert seller_history["total"] == 1
    assert seller_history["balance"] == 125.0
    assert len(seller_history["entries"]) == 1

    seller_entry = seller_history["entries"][0]
    assert seller_entry["transaction_type"] == "SALE"
    assert seller_entry["amount"] == 125.0
    assert seller_entry["balance_after"] == 125.0

    product_history = _get_product_history(api_client, product_id, buyer["token"])
    assert [entry["to_state"] for entry in product_history] == ["available", "reserved", "sold"]
    assert product_history[-1]["changed_by"] == buyer["email"]


def test_purchase_flow_rejects_insufficient_funds_without_creating_purchase_ledger_entries(
    api_client,
    seller,
    buyer,
):
    product = _create_product(api_client, seller["token"], price=300.0)
    product_id = product[PRODUCT_ID_FIELD]

    _top_up_wallet(api_client, buyer["token"], amount=50.0)

    reservation = _reserve_product(api_client, product_id, buyer["token"])
    assert reservation["state"] == "reserved"

    purchase_response = _buy_product(api_client, product_id, buyer["token"])
    assert purchase_response.status_code == 402, purchase_response.text
    assert "Insufficient funds" in purchase_response.text

    buyer_history = _get_wallet_history(api_client, buyer["token"])
    assert buyer_history["total"] == 1
    assert len(buyer_history["entries"]) == 1
    assert buyer_history["entries"][0]["transaction_type"] == "TOP_UP"
    assert buyer_history["entries"][0]["balance_after"] == 50.0

    seller_history = _get_wallet_history(api_client, seller["token"])
    assert seller_history["total"] == 0
    assert seller_history["entries"] == []

    product_history = _get_product_history(api_client, product_id, buyer["token"])
    assert product_history[-1]["to_state"] == "reserved"