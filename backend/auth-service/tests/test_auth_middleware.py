from datetime import datetime, timedelta

from jose import jwt

from app.core.security import SECRET_KEY, ALGORITHM


def test_protected_without_token(client):
    response = client.get("/auth/protected")

    assert response.status_code == 401


def test_protected_with_valid_token(client):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "protected_ok@example.com",
            "password": "1234"
        }
    )

    token = register_response.json()["access_token"]

    response = client.get(
        "/auth/protected",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "acceso permitido"
    assert data["user"] == "protected_ok@example.com"


def test_protected_with_invalid_token(client):
    response = client.get(
        "/auth/protected",
        headers={"Authorization": "Bearer token_falso"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido"


def test_protected_with_expired_token(client):
    expired_payload = {
        "sub": "expired@example.com",
        "exp": datetime.utcnow() - timedelta(minutes=5)
    }

    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

    response = client.get(
        "/auth/protected",
        headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido"