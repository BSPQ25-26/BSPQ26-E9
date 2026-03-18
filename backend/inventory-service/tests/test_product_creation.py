

import pytest
from app.models.product import ProductState

def get_auth_header():
    # Simula un usuario autenticado (ajusta según tu sistema de auth real)
    return {"Authorization": "testtoken"}

def test_create_product_success(client):
    product_data = {
        "title": "Producto Test",
        "description": "Descripción de prueba",
        "category": "Electrónica",
        "price": 100.0,
        "condition": "Nuevo"
    }
    response = client.post("/api/v1/products", json=product_data, headers=get_auth_header())
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == product_data["title"]
    assert data["state"] == ProductState.AVAILABLE

def test_create_product_missing_field(client):
    product_data = {
        "title": "Producto Test",
        "description": "Descripción de prueba",
        "category": "Electrónica",
        # Falta el campo price
        "condition": "Nuevo"
    }
    response = client.post("/api/v1/products", json=product_data, headers=get_auth_header())
    assert response.status_code == 422

def test_create_product_invalid_price(client):
    product_data = {
        "title": "Producto Test",
        "description": "Descripción de prueba",
        "category": "Electrónica",
        "price": -10.0,
        "condition": "Nuevo"
    }
    response = client.post("/api/v1/products", json=product_data, headers=get_auth_header())
    assert response.status_code == 422

def test_create_product_unauthorized(client):
    product_data = {
        "title": "Producto Test",
        "description": "Descripción de prueba",
        "category": "Electrónica",
        "price": 100.0,
        "condition": "Nuevo"
    }
    response = client.post("/api/v1/products", json=product_data)  # Sin header de auth
    assert response.status_code == 401
