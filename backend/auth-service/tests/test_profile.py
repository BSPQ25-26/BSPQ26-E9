def _register_and_login(client, email, password="1234"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def test_profile_returns_correct_data(client):
    _register_and_login(client, "user1@example.com")

    response = client.get("/users/1/profile")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "user1@example.com"
    assert "member_since" in data
    assert "avg_rating" in data
    assert "active_listing_count" in data


def test_profile_can_be_resolved_by_username(client):
    _register_and_login(client, "seller@example.com")

    response = client.get("/users/resolve", params={"username": "seller@example.com"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "seller@example.com"


def test_profile_user_without_ratings_has_null_avg(client):
    _register_and_login(client, "noratings@example.com")

    response = client.get("/users/1/profile")

    assert response.status_code == 200
    assert response.json()["avg_rating"] is None


def test_profile_is_public_no_token_needed(client):
    _register_and_login(client, "public@example.com")

    response = client.get("/users/1/profile")

    assert response.status_code == 200


def test_profile_products_returns_active_listings(client):
    from unittest.mock import patch

    _register_and_login(client, "seller@example.com")

    with patch("app.api.v1.user_router.httpx.get") as inventory_get:
        inventory_get.return_value.status_code = 200
        inventory_get.return_value.json.return_value = [
            {
                "id": 1,
                "seller_id": "seller@example.com",
                "state": "Available",
                "title": "Oak side table",
            },
            {
                "id": 2,
                "seller_id": "seller@example.com",
                "state": "Sold",
                "title": "Sold table",
            },
            {
                "id": 3,
                "seller_id": "other@example.com",
                "state": "Available",
                "title": "Other item",
            },
        ]

        response = client.get("/users/1/products")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "seller_id": "seller@example.com",
            "state": "Available",
            "title": "Oak side table",
        },
    ]


def test_profile_not_found_returns_404(client):
    response = client.get("/users/9999/profile")

    assert response.status_code == 404
    assert response.json()["detail"] == "Usuario no encontrado"


def test_ratings_list_is_paginated(client):
    from unittest.mock import patch

    token = _register_and_login(client, "rater@example.com")
    client.post("/auth/register", json={"email": "rated@example.com", "password": "1234"})

    transaction = {
        "buyer_id": "rater@example.com",
        "seller_id": "rated@example.com",
        "status": "completed",
    }

    with patch("app.services.rating_service._check_transaction_eligibility", return_value=transaction):
        for i in range(1, 4):
            client.post(
                "/ratings",
                json={"to_user_id": 2, "transaction_id": i, "stars": 4},
                headers={"Authorization": f"Bearer {token}"}
            )

    response_page1 = client.get("/users/2/ratings?skip=0&limit=2")
    response_page2 = client.get("/users/2/ratings?skip=2&limit=2")

    assert response_page1.status_code == 200
    assert len(response_page1.json()) == 2
    assert response_page2.status_code == 200
    assert len(response_page2.json()) == 1
