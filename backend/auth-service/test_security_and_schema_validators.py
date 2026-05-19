from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from pydantic import ValidationError

#cd backend\auth-service
#python -m pytest test_security_and_schema_validators.py -q

from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.schemas.auth import LoginRequest, RegisterRequest


def test_hash_password_and_verify_password_round_trip():
    password_hash = hash_password("s3cret-password")

    assert verify_password("s3cret-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_create_access_token_encodes_subject_and_verify_token_decodes_it():
    token = create_access_token({"sub": "user@example.com"})

    assert verify_token(token) == "user@example.com"


def test_verify_token_rejects_expired_token():
    token = jwt.encode(
        {
            "sub": "expired@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    assert verify_token(token) is None


def test_verify_token_rejects_tampered_token():
    token = create_access_token({"sub": "user@example.com"})

    assert verify_token(f"{token}broken") is None


@pytest.mark.parametrize(
    "schema_cls",
    [RegisterRequest, LoginRequest],
)
def test_auth_request_schema_accepts_valid_email(schema_cls):
    request = schema_cls(email="valid@example.com", password="secret")

    assert request.email == "valid@example.com"
    assert request.password == "secret"


@pytest.mark.parametrize(
    "schema_cls",
    [RegisterRequest, LoginRequest],
)
def test_auth_request_schema_rejects_invalid_email(schema_cls):
    with pytest.raises(ValidationError) as exc_info:
        schema_cls(email="correo-invalido", password="secret")

    assert "email" in str(exc_info.value)