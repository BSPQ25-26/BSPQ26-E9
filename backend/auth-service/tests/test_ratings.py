from unittest.mock import patch


def _completed_transaction(buyer="rater@example.com", seller="rated@example.com"):
    return {
        "buyer_id": buyer,
        "seller_id": seller,
        "status": "completed",
    }


def _register_and_login(client, email, password="1234"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def test_create_rating_success(client):
    token = _register_and_login(client, "rater@example.com")
    client.post("/auth/register", json={"email": "rated@example.com", "password": "1234"})

    with patch(
        "app.services.rating_service._check_transaction_eligibility",
        return_value=_completed_transaction(),
    ):
        response = client.post(
            "/ratings",
            json={"to_user_id": 2, "transaction_id": 10, "stars": 5, "review_text": "Excelente"},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "valoración creada correctamente"
    assert "rating_id" in data


def test_create_rating_duplicate_returns_409(client):
    token = _register_and_login(client, "rater@example.com")
    client.post("/auth/register", json={"email": "rated@example.com", "password": "1234"})

    payload = {"to_user_id": 2, "transaction_id": 99, "stars": 4}

    with patch(
        "app.services.rating_service._check_transaction_eligibility",
        return_value=_completed_transaction(),
    ):
        client.post("/ratings", json=payload, headers={"Authorization": f"Bearer {token}"})
        response = client.post("/ratings", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya has valorado esta transacción"


def test_create_rating_invalid_stars_returns_422(client):
    token = _register_and_login(client, "rater@example.com")

    response = client.post(
        "/ratings",
        json={"to_user_id": 2, "transaction_id": 50, "stars": 10},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 422


def test_create_rating_without_token_returns_401(client):
    response = client.post(
        "/ratings",
        json={"to_user_id": 2, "transaction_id": 77, "stars": 3}
    )

    assert response.status_code == 401


def test_create_rating_rejects_non_counterparty_target(client):
    token = _register_and_login(client, "rater@example.com")
    client.post("/auth/register", json={"email": "rated@example.com", "password": "1234"})
    client.post("/auth/register", json={"email": "other@example.com", "password": "1234"})

    with patch(
        "app.services.rating_service._check_transaction_eligibility",
        return_value=_completed_transaction(),
    ):
        response = client.post(
            "/ratings",
            json={"to_user_id": 3, "transaction_id": 10, "stars": 5},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Solo puedes valorar a la otra parte de la transacción"


def test_avg_rating_recalculated_after_multiple_ratings(client):
    token = _register_and_login(client, "rater@example.com")
    client.post("/auth/register", json={"email": "rated@example.com", "password": "1234"})

    with patch(
        "app.services.rating_service._check_transaction_eligibility",
        return_value=_completed_transaction(),
    ):
        client.post(
            "/ratings",
            json={"to_user_id": 2, "transaction_id": 1, "stars": 4},
            headers={"Authorization": f"Bearer {token}"}
        )
        response = client.post(
            "/ratings",
            json={"to_user_id": 2, "transaction_id": 2, "stars": 2},
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
