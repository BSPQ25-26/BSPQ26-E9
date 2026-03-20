import os
from uuid import uuid4

import httpx
import pytest

# running auth-service in 8001 & transaction-service in 8003 is required for these tests to work
# $env:RUN_STATE_MACHINE_INTEGRATION="1"; python.exe -m pytest tests/integration/test_state_machine_integration.py -v


RUN_INTEGRATION = os.getenv("RUN_STATE_MACHINE_INTEGRATION") == "1"
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8001")
TRANSACTION_BASE_URL = os.getenv("TRANSACTION_BASE_URL", "http://localhost:8003")
PRODUCTS_PATH = os.getenv("PRODUCTS_PATH", "/products")
PRODUCT_ID_FIELD = os.getenv("PRODUCT_ID_FIELD", "id")

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_STATE_MACHINE_INTEGRATION=1 to run state machine integration tests.",
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
        "title": f"state-test-{uuid4().hex[:6]}",
        "description": "state machine integration test product",
        "price": 100.0,
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


def _transition_product_state(client: httpx.Client, product_id: int, owner_token: str, target_state: str) -> httpx.Response:
    """Attempt state transition and return response."""
    try:
        return client.patch(
            f"{TRANSACTION_BASE_URL}{PRODUCTS_PATH}/{product_id}/state",
            json={"target_state": target_state},
            headers=_headers(owner_token),
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable: {exc}")


def _get_state_history(client: httpx.Client, product_id: int, owner_token: str) -> list:
    """Retrieve state history for a product."""
    try:
        response = client.get(
            f"{TRANSACTION_BASE_URL}{PRODUCTS_PATH}/{product_id}/history",
            headers=_headers(owner_token),
        )
        assert response.status_code == 200, f"Get history failed: {response.text}"
        return response.json()
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable: {exc}")


@pytest.fixture()
def api_client():
    with httpx.Client(timeout=20.0) as client:
        yield client


@pytest.fixture()
def owner(api_client):
    try:
        return _create_and_login_user(api_client, "owner-state")
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Auth service unreachable: {exc}")


@pytest.fixture()
def other_user(api_client):
    try:
        return _create_and_login_user(api_client, "other-user-state")
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Auth service unreachable: {exc}")


@pytest.fixture()
def product(api_client, owner):
    return _create_product(api_client, owner["token"])


def test_product_starts_in_available_state(api_client, owner):
    """Newly created products start in the AVAILABLE state."""
    prod = _create_product(api_client, owner["token"])
    assert prod["state"] == "available", f"Expected 'available', got {prod['state']}"


def test_state_history_records_initial_available_state(api_client, owner):
    """State history should have an initial entry recording AVAILABLE state."""
    prod = _create_product(api_client, owner["token"])
    product_id = prod[PRODUCT_ID_FIELD]

    history = _get_state_history(api_client, product_id, owner["token"])
    assert len(history) >= 1, "State history should have at least one entry (initial state)"

    initial = history[0]
    assert initial["to_state"] == "available", f"Initial state should be 'available', got {initial['to_state']}"
    assert initial["from_state"] is None, f"Initial state should have from_state=None, got {initial['from_state']}"


def test_available_to_reserved_transition_is_valid_and_recorded(api_client, owner, product):
    """Available → Reserved is a valid transition and should be recorded in history."""
    product_id = product[PRODUCT_ID_FIELD]

    # Transition to RESERVED
    response = _transition_product_state(api_client, product_id, owner["token"], "reserved")
    assert response.status_code in (200, 202), f"Transition failed: {response.text}"

    transition_data = response.json()
    assert transition_data["from_state"] == "available"
    assert transition_data["to_state"] == "reserved"

    # Verify state history was recorded
    history = _get_state_history(api_client, product_id, owner["token"])
    assert len(history) >= 2, f"Expected at least 2 history entries, got {len(history)}"

    found_transition = any(
        h["from_state"] == "available" and h["to_state"] == "reserved"
        for h in history
    )
    assert found_transition, "Transition from available to reserved not found in history"


def test_reserved_to_sold_transition_is_valid_and_recorded(api_client, owner, product):
    """Reserved → Sold is a valid transition and should be recorded in history."""
    product_id = product[PRODUCT_ID_FIELD]

    # Transition to RESERVED first
    response1 = _transition_product_state(api_client, product_id, owner["token"], "reserved")
    assert response1.status_code in (200, 202), f"First transition failed: {response1.text}"

    # Then to SOLD
    response2 = _transition_product_state(api_client, product_id, owner["token"], "sold")
    assert response2.status_code in (200, 202), f"Second transition failed: {response2.text}"

    transition_data = response2.json()
    assert transition_data["from_state"] == "reserved"
    assert transition_data["to_state"] == "sold"

    # Verify state history has both transitions
    history = _get_state_history(api_client, product_id, owner["token"])
    assert len(history) >= 3, f"Expected at least 3 history entries, got {len(history)}"

    found_transition = any(
        h["from_state"] == "reserved" and h["to_state"] == "sold"
        for h in history
    )
    assert found_transition, "Transition from reserved to sold not found in history"


def test_available_to_sold_direct_transition_is_invalid(api_client, owner, product):
    """Available → Sold directly is NOT allowed (must go through Reserved)."""
    product_id = product[PRODUCT_ID_FIELD]

    response = _transition_product_state(api_client, product_id, owner["token"], "sold")
    assert response.status_code == 422, (
        f"Expected 422 (Unprocessable Entity) for invalid transition, got {response.status_code}: {response.text}"
    )


def test_reserved_to_available_reverse_transition_is_invalid(api_client, owner, product):
    """Reserved → Available (going backwards) is NOT allowed."""
    product_id = product[PRODUCT_ID_FIELD]

    # First, transition to RESERVED
    response1 = _transition_product_state(api_client, product_id, owner["token"], "reserved")
    assert response1.status_code in (200, 202)

    # Now try to go back to AVAILABLE
    response2 = _transition_product_state(api_client, product_id, owner["token"], "available")
    assert response2.status_code == 422, (
        f"Expected 422 for reverse transition, got {response2.status_code}: {response2.text}"
    )


def test_sold_state_is_final_no_transitions_allowed(api_client, owner, product):
    """Sold is a final state; no transitions should be allowed from Sold."""
    product_id = product[PRODUCT_ID_FIELD]

    # Transition to RESERVED, then SOLD
    _transition_product_state(api_client, product_id, owner["token"], "reserved")
    response1 = _transition_product_state(api_client, product_id, owner["token"], "sold")
    assert response1.status_code in (200, 202)

    # Try to transition FROM SOLD (should fail)
    response2 = _transition_product_state(api_client, product_id, owner["token"], "available")
    assert response2.status_code == 422, (
        f"Expected 422 for transition from Sold state, got {response2.status_code}: {response2.text}"
    )

    response3 = _transition_product_state(api_client, product_id, owner["token"], "reserved")
    assert response3.status_code == 422, (
        f"Expected 422 for transition from Sold state, got {response3.status_code}: {response3.text}"
    )


def test_state_transitions_require_product_ownership(api_client, owner, other_user, product):
    """Non-owner cannot transition product state (should get 403)."""
    product_id = product[PRODUCT_ID_FIELD]

    response = _transition_product_state(api_client, product_id, other_user["token"], "reserved")
    assert response.status_code == 403, (
        f"Expected 403 (Forbidden) for non-owner state transition, got {response.status_code}: {response.text}"
    )


def test_state_transitions_require_authentication(api_client, product):
    """Unauthenticated requests should fail (401)."""
    product_id = product[PRODUCT_ID_FIELD]

    try:
        response = api_client.patch(
            f"{TRANSACTION_BASE_URL}{PRODUCTS_PATH}/{product_id}/state",
            json={"target_state": "reserved"},
        )
    except _CONNECT_ERRORS as exc:
        pytest.skip(f"Transaction service unreachable: {exc}")

    assert response.status_code == 401, (
        f"Expected 401 (Unauthorized) without token, got {response.status_code}: {response.text}"
    )


def test_state_history_records_changed_by_field(api_client, owner, product):
    """State history entries should record which user made the transition."""
    product_id = product[PRODUCT_ID_FIELD]

    _transition_product_state(api_client, product_id, owner["token"], "reserved")

    history = _get_state_history(api_client, product_id, owner["token"])
    assert len(history) >= 2

    # Find the transition to RESERVED and verify changed_by is recorded
    reserved_entry = next((h for h in history if h["to_state"] == "reserved"), None)
    assert reserved_entry is not None, "No entry found for transition to reserved"
    assert "changed_by" in reserved_entry, "History entry missing 'changed_by' field"
    assert reserved_entry["changed_by"] is not None, "'changed_by' should not be None"


def test_state_history_records_changed_at_timestamp(api_client, owner, product):
    """State history entries should have a changed_at timestamp."""
    product_id = product[PRODUCT_ID_FIELD]

    _transition_product_state(api_client, product_id, owner["token"], "reserved")

    history = _get_state_history(api_client, product_id, owner["token"])

    for entry in history:
        assert "changed_at" in entry, "History entry missing 'changed_at' field"
        assert entry["changed_at"] is not None, "'changed_at' should not be None"


def test_full_state_lifecycle_available_to_reserved_to_sold(api_client, owner, product):
    """Full lifecycle: Available → Reserved → Sold with complete history."""
    product_id = product[PRODUCT_ID_FIELD]

    # Initial state
    history = _get_state_history(api_client, product_id, owner["token"])
    assert len(history) == 1
    assert history[0]["to_state"] == "available"

    # Transition to RESERVED
    resp1 = _transition_product_state(api_client, product_id, owner["token"], "reserved")
    assert resp1.status_code in (200, 202)

    history = _get_state_history(api_client, product_id, owner["token"])
    assert len(history) == 2
    assert history[1]["to_state"] == "reserved"

    # Transition to SOLD
    resp2 = _transition_product_state(api_client, product_id, owner["token"], "sold")
    assert resp2.status_code in (200, 202)

    history = _get_state_history(api_client, product_id, owner["token"])
    assert len(history) == 3
    assert history[2]["to_state"] == "sold"

    # Verify transitions in order
    assert history[0]["to_state"] == "available"
    assert history[1]["from_state"] == "available" and history[1]["to_state"] == "reserved"
    assert history[2]["from_state"] == "reserved" and history[2]["to_state"] == "sold"
