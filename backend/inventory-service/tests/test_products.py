from app.models.product import Product


def _product_payload(**overrides):
    payload = {
        "title": "Vintage camera",
        "description": "Well maintained film camera.",
        "category": "electronics",
        "price": 149.99,
        "condition": "New",
    }
    payload.update(overrides)
    return payload


def _create_product(client, headers, **overrides):
    return client.post("/api/v1/products", json=_product_payload(**overrides), headers=headers)


def test_create_product_success(client, db_session, auth_headers):
    response = _create_product(client, auth_headers)

    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Vintage camera"
    assert data["description"] == "Well maintained film camera."
    assert data["category"] == "electronics"
    assert data["price"] == 149.99
    assert data["condition"] == "New"
    assert data["state"] == "Available"
    assert data["seller_id"] == "seller@example.com"
    assert "created_at" in data

    stored_product = db_session.query(Product).filter(Product.id == data["id"]).first()
    assert stored_product is not None
    assert stored_product.state.value == "Available"
    assert stored_product.seller_id == "seller@example.com"


def test_create_product_missing_required_field_returns_422(client, auth_headers):
    payload = _product_payload()
    payload.pop("title")

    response = client.post("/api/v1/products", json=payload, headers=auth_headers)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"][-1] == "title" for error in errors)


def test_create_product_invalid_price_returns_422(client, auth_headers):
    for invalid_price in (-10, 0):
        response = _create_product(client, auth_headers, price=invalid_price)

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any(error["loc"][-1] == "price" for error in errors)


def test_create_product_without_token_returns_401(client):
    response = client.post("/api/v1/products", json=_product_payload())

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_update_product_success_by_owner(client, auth_headers):
    created_response = _create_product(client, auth_headers)
    product_id = created_response.json()["id"]

    response = client.put(
        f"/api/v1/products/{product_id}",
        json={
            "title": "Updated camera",
            "description": "Now includes the carrying case.",
            "category": "collectibles",
            "price": 179.5,
            "condition": "Like New",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Updated camera"
    assert data["description"] == "Now includes the carrying case."
    assert data["category"] == "collectibles"
    assert data["price"] == 179.5
    assert data["condition"] == "Like New"
    assert data["seller_id"] == "seller@example.com"
def test_create_product_invalid_condition_returns_422(client, auth_headers):
    response = _create_product(client, auth_headers, condition="refurbished")
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"][-1] == "condition" for error in errors)


def test_partial_update_only_changes_supplied_fields(client, auth_headers):
    created_response = _create_product(client, auth_headers)
    original = created_response.json()

    response = client.put(
        f"/api/v1/products/{original['id']}",
        json={"description": "Updated description only."},
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["description"] == "Updated description only."
    assert data["title"] == original["title"]
    assert data["category"] == original["category"]
    assert data["price"] == original["price"]
    assert data["condition"] == original["condition"]


def test_update_product_forbidden_for_non_owner(client, auth_headers, other_seller_token):
    created_response = _create_product(client, auth_headers)
    product_id = created_response.json()["id"]

    response = client.put(
        f"/api/v1/products/{product_id}",
        json={"price": 190},
        headers={"Authorization": f"Bearer {other_seller_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_delete_product_success_by_owner(client, db_session, auth_headers):
    created_response = _create_product(client, auth_headers)
    product_id = created_response.json()["id"]

    response = client.delete(f"/api/v1/products/{product_id}", headers=auth_headers)

    assert response.status_code == 204
    assert db_session.query(Product).filter(Product.id == product_id).first() is None


def test_delete_product_forbidden_for_non_owner(client, auth_headers, other_seller_token):
    created_response = _create_product(client, auth_headers)
    product_id = created_response.json()["id"]

    response = client.delete(
        f"/api/v1/products/{product_id}",
        headers={"Authorization": f"Bearer {other_seller_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_update_missing_product_returns_404(client, auth_headers):
    response = client.put(
        "/api/v1/products/99999",
        json={"price": 220},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_delete_missing_product_returns_404(client, auth_headers):
    response = client.delete("/api/v1/products/99999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"