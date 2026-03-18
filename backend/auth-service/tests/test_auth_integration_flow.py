from datetime import datetime, timezone

from jose import jwt

from app.core.security import ALGORITHM, SECRET_KEY

# commnand to run this test:
#& ".\.venv\Scripts\python.exe" -m pytest backend/auth-service/tests -q

def _assert_valid_token_for_user(token: str, expected_email: str) -> None:
    header = jwt.get_unverified_header(token)
    assert header["alg"] == ALGORITHM

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["sub"] == expected_email
    assert "exp" in payload
    assert datetime.fromtimestamp(payload["exp"], tz=timezone.utc) > datetime.now(timezone.utc)


def test_register_login_and_access_protected_flow(client):
    email = "integration_flow@example.com"
    password = "1234"

    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )

    assert register_response.status_code == 200
    register_data = register_response.json()
    assert register_data["token_type"] == "bearer"
    _assert_valid_token_for_user(register_data["access_token"], email)

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )

    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["message"] == "login correcto"
    assert login_data["token_type"] == "bearer"
    _assert_valid_token_for_user(login_data["access_token"], email)

    protected_response = client.get(
        "/auth/protected",
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )

    assert protected_response.status_code == 200
    protected_data = protected_response.json()
    assert protected_data["message"] == "acceso permitido"
    assert protected_data["user"] == email
