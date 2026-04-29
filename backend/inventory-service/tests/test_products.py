from app.models.product import Product
import io
#pytest test_products.py -k "upload" -q

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


def _catalog_titles(client, headers, **params):
    response = client.get("/api/v1/products", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return {item["title"] for item in response.json()}


def _seed_catalog_products(client, headers, db_session):
    created = {}
    fixtures = [
        ("phone", {"title": "Phone A", "category": "electronics", "price": 100, "condition": "New"}),
        ("laptop", {"title": "Laptop B", "category": "electronics", "price": 300, "condition": "Like New"}),
        ("chair", {"title": "Chair C", "category": "furniture", "price": 80, "condition": "Good"}),
        ("table", {"title": "Table D", "category": "furniture", "price": 150, "condition": "Fair"}),
        ("book", {"title": "Book E", "category": "books", "price": 20, "condition": "Poor"}),
    ]

    for key, payload in fixtures:
        response = _create_product(client, headers, **payload)
        assert response.status_code == 201, response.text
        created[key] = response.json()

    sold_product = db_session.query(Product).filter(Product.id == created["laptop"]["id"]).first()
    reserved_product = db_session.query(Product).filter(Product.id == created["chair"]["id"]).first()
    sold_product.state = "Sold"
    reserved_product.state = "Reserved"
    db_session.commit()

    return created


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


def test_catalog_filters_all_combinations_return_expected_products(client, auth_headers, db_session):
    _seed_catalog_products(client, auth_headers, db_session)

    assert _catalog_titles(client, auth_headers, state="Available") == {"Phone A", "Table D", "Book E"}
    assert _catalog_titles(client, auth_headers, category="electronics") == {"Phone A", "Laptop B"}
    assert _catalog_titles(client, auth_headers, min_price=90, max_price=200) == {"Phone A", "Table D"}
    assert _catalog_titles(client, auth_headers, condition="Like New") == {"Laptop B"}

    assert _catalog_titles(
        client,
        auth_headers,
        state="Available",
        category="furniture",
    ) == {"Table D"}

    assert _catalog_titles(
        client,
        auth_headers,
        state="Reserved",
        category="furniture",
        condition="Good",
    ) == {"Chair C"}

    assert _catalog_titles(
        client,
        auth_headers,
        state="Sold",
        category="electronics",
        min_price=250,
        max_price=350,
        condition="Like New",
    ) == {"Laptop B"}

    assert _catalog_titles(
        client,
        auth_headers,
        state="Available",
        category="electronics",
        min_price=50,
        max_price=120,
        condition="New",
    ) == {"Phone A"}

    assert _catalog_titles(
        client,
        auth_headers,
        state="Reserved",
        category="books",
        min_price=100,
        max_price=120,
    ) == set()


def test_catalog_filters_reject_invalid_price_range(client, auth_headers, db_session):
    _seed_catalog_products(client, auth_headers, db_session)

    response = client.get(
        "/api/v1/products",
        params={"min_price": 200, "max_price": 100},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "min_price cannot be greater than max_price"


def test_upload_image_success(client, auth_headers):
    created = _create_product(client, auth_headers)
    product_id = created.json()["id"]

    file = io.BytesIO(b"fake image data")
    
    response = client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("test.png", file, "image/png")},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert "image_url" in payload
    assert payload["image_url"].startswith("/uploads/")


def test_uploaded_image_urls_appear_in_get_product_response(client, auth_headers):
    created = _create_product(client, auth_headers)
    product_id = created.json()["id"]

    upload_1 = client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("first.png", io.BytesIO(b"img-1"), "image/png")},
        headers=auth_headers,
    )
    upload_2 = client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("second.jpg", io.BytesIO(b"img-2"), "image/jpeg")},
        headers=auth_headers,
    )

    assert upload_1.status_code == 200, upload_1.text
    assert upload_2.status_code == 200, upload_2.text

    product_get = client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
    assert product_get.status_code == 200, product_get.text

    product = product_get.json()
    assert "images" in product
    assert isinstance(product["images"], list)
    assert upload_1.json()["image_url"] in product["images"]
    assert upload_2.json()["image_url"] in product["images"]
    assert len(product["images"]) == 2


def test_upload_invalid_format_returns_422(client, auth_headers):
    created = _create_product(client, auth_headers)
    product_id = created.json()["id"]

    file = io.BytesIO(b"not an image")

    response = client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("test.txt", file, "text/plain")},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid file format"


def test_upload_oversized_file_returns_422(client, auth_headers):
    created = _create_product(client, auth_headers)
    product_id = created.json()["id"]

    big_file = io.BytesIO(b"a" * (6 * 1024 * 1024))  # 6MB

    response = client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("big.png", big_file, "image/png")},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "File too large"


def test_upload_image_non_owner_forbidden(client, auth_headers, other_seller_token):
    created = _create_product(client, auth_headers)
    product_id = created.json()["id"]

    file = io.BytesIO(b"fake image data")

    response = client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("test.png", file, "image/png")},
        headers={"Authorization": f"Bearer {other_seller_token}"},
    )

    assert response.status_code == 403


def test_upload_exceed_image_limit(client, auth_headers):
    created = _create_product(client, auth_headers)
    product_id = created.json()["id"]

    for _ in range(8):
        file = io.BytesIO(b"img")
        client.post(
            f"/api/v1/products/{product_id}/images",
            files={"file": ("test.png", file, "image/png")},
            headers=auth_headers,
        )

    extra_file = io.BytesIO(b"img")

    response = client.post(
        f"/api/v1/products/{product_id}/images",
        files={"file": ("extra.png", extra_file, "image/png")},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Image limit exceeded"

