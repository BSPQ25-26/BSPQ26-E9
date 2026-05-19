import pytest
from pydantic import ValidationError

from app.schemas.product import ProductCondition, ProductCreate, ProductState, ProductUpdate
#cd backend\inventory-service
#python -m pytest tests\test_schema_validators.py -q

def test_product_create_accepts_valid_payload_and_defaults_condition():
    product = ProductCreate(
        title="Camera",
        description="Working film camera",
        category="electronics",
        price=149.99,
    )

    assert product.title == "Camera"
    assert product.condition == ProductCondition.NEW


@pytest.mark.parametrize(
    "field_name,payload",
    [
        ("title", {"title": "", "description": "Working", "category": "electronics", "price": 1.0}),
        ("description", {"title": "Camera", "description": "", "category": "electronics", "price": 1.0}),
        ("category", {"title": "Camera", "description": "Working", "category": "", "price": 1.0}),
        ("price", {"title": "Camera", "description": "Working", "category": "electronics", "price": 0}),
    ],
)
def test_product_create_rejects_invalid_fields(field_name, payload):
    with pytest.raises(ValidationError) as exc_info:
        ProductCreate(**payload)

    assert field_name in str(exc_info.value)


def test_product_create_normalizes_legacy_name_field():
    product = ProductCreate(
        name="Legacy Camera",
        description="Old payload format",
        category="electronics",
        price=99.0,
    )

    assert product.title == "Legacy Camera"
    assert product.condition == ProductCondition.NEW


def test_product_update_accepts_legacy_name_and_ignores_stock():
    update = ProductUpdate(name="Updated Camera", stock=3, price=120.0)

    assert update.title == "Updated Camera"
    assert update.price == 120.0
    assert update.transaction_product_id is None


def test_product_update_rejects_empty_strings_and_extra_fields():
    with pytest.raises(ValidationError):
        ProductUpdate(title="", description="ok")

    with pytest.raises(ValidationError):
        ProductUpdate(title="Camera", unsupported_field=True)


def test_product_state_enum_values_are_accepted_by_update_schema():
    update = ProductUpdate(condition=ProductCondition.GOOD)

    assert update.condition == ProductCondition.GOOD


def test_product_out_state_enum_matches_expected_serialized_values():
    assert ProductState.AVAILABLE.value == "Available"
    assert ProductState.RESERVED.value == "Reserved"
    assert ProductState.SOLD.value == "Sold"