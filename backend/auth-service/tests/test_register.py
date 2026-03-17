def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "register_ok@example.com",
            "password": "1234"
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "usuario creado correctamente"
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate(client):
    client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "1234"
        }
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "1234"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "El usuario ya existe"


def test_register_invalid_email(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "correo-invalido",
            "password": "1234"
        }
    )

    assert response.status_code == 422