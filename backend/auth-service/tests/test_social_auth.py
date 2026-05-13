import pytest
from fastapi import HTTPException

from app.models.user import User
from app.models.social_account import SocialAccount
from app.api.v1.social_auth_router import _handle_social_login
from app.core.security import hash_password


def test_handle_social_login_creates_new_user(client, db):
    """Un usuario nuevo que hace login social se crea correctamente."""
    result = _handle_social_login(db, "newuser@example.com", "google_123", "google")

    assert "access_token" in result
    assert result["token_type"] == "bearer"

    user = db.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.password_hash == ""

    social = db.query(SocialAccount).filter(
        SocialAccount.provider == "google",
        SocialAccount.provider_user_id == "google_123"
    ).first()
    assert social is not None
    assert social.user_id == user.id


def test_handle_social_login_links_existing_email_user(client, db):
    """Un usuario con email/password existente se vincula al provider social."""
    existing_user = User(
        email="existing@example.com",
        password_hash=hash_password("password123"),
        wallet_balance=0.0,
    )
    db.add(existing_user)
    db.commit()
    db.refresh(existing_user)
    original_id = existing_user.id

    result = _handle_social_login(db, "existing@example.com", "google_456", "google")

    assert "access_token" in result
    social = db.query(SocialAccount).filter(
        SocialAccount.provider == "google",
        SocialAccount.provider_user_id == "google_456"
    ).first()
    assert social is not None
    assert social.user_id == original_id


def test_handle_social_login_duplicate_provider_returns_409(client, db):
    """Mismo email vinculado a dos providers distintos devuelve 409."""
    _handle_social_login(db, "dupuser@example.com", "google_789", "google")

    with pytest.raises(HTTPException) as exc_info:
        _handle_social_login(db, "dupuser@example.com", "facebook_789", "facebook")

    assert exc_info.value.status_code == 409
    assert "google" in exc_info.value.detail


def test_handle_social_login_same_provider_returns_token(client, db):
    """El mismo usuario haciendo login con el mismo provider devuelve token sin error."""
    result1 = _handle_social_login(db, "returning@example.com", "google_abc", "google")
    result2 = _handle_social_login(db, "returning@example.com", "google_abc", "google")

    assert "access_token" in result1
    assert "access_token" in result2


def test_login_blocked_for_oauth_only_account(client, db):
    """Login con password falla para cuentas creadas via OAuth."""
    _handle_social_login(db, "oauthonly@example.com", "google_xyz", "google")
    db.close()

    response = client.post(
        "/auth/login",
        json={"email": "oauthonly@example.com", "password": "cualquiercosa"}
    )

    assert response.status_code == 401
    assert "login social" in response.json()["detail"]
