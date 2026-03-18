"""
Verify JWT of auth-service for knowing the user making the request 
"""
from jose import jwt, JWTError
from app.core.config import settings


def verify_token(token: str) -> str | None:
    """Verifies JWT and returns the user identifier (email or id), or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return user_id  # returns the user email
    except (JWTError, ValueError):
        return None