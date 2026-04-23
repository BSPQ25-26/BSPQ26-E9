import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.db.session import get_db
from app.models.user import User
from app.models.social_account import SocialAccount
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["social-auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8001/auth/google/callback")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8001/auth/facebook/callback")

FACEBOOK_AUTH_URL = "https://www.facebook.com/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
FACEBOOK_USERINFO_URL = "https://graph.facebook.com/me?fields=id,email"


@router.get("/google")
async def google_login():
    async with AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        redirect_uri=GOOGLE_REDIRECT_URI,
    ) as client:
        uri, _ = client.create_authorization_url(
            GOOGLE_AUTH_URL,
            scope="openid email profile",
        )
    return RedirectResponse(uri)


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    async with AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=GOOGLE_REDIRECT_URI,
    ) as client:
        token = await client.fetch_token(GOOGLE_TOKEN_URL, code=code)
        resp = await client.get(GOOGLE_USERINFO_URL)
        user_info = resp.json()

    email = user_info.get("email")
    provider_user_id = user_info.get("id")

    if not email or not provider_user_id:
        raise HTTPException(status_code=400, detail="No se pudo obtener el email de Google")

    return _handle_social_login(db, email, provider_user_id, "google")


@router.get("/facebook")
async def facebook_login():
    async with AsyncOAuth2Client(
        client_id=FACEBOOK_CLIENT_ID,
        redirect_uri=FACEBOOK_REDIRECT_URI,
    ) as client:
        uri, _ = client.create_authorization_url(
            FACEBOOK_AUTH_URL,
            scope="public_profile,email",
        )
    return RedirectResponse(uri)


@router.get("/facebook/callback")
async def facebook_callback(code: str, db: Session = Depends(get_db)):
    async with AsyncOAuth2Client(
        client_id=FACEBOOK_CLIENT_ID,
        client_secret=FACEBOOK_CLIENT_SECRET,
        redirect_uri=FACEBOOK_REDIRECT_URI,
    ) as client:
        token = await client.fetch_token(FACEBOOK_TOKEN_URL, code=code)
        resp = await client.get(FACEBOOK_USERINFO_URL)
        user_info = resp.json()

    email = user_info.get("email")
    provider_user_id = user_info.get("id")

    if not email or not provider_user_id:
        raise HTTPException(status_code=400, detail="No se pudo obtener el email de Facebook")

    return _handle_social_login(db, email, provider_user_id, "facebook")


def _handle_social_login(db: Session, email: str, provider_user_id: str, provider: str):
    # Buscar si ya existe la cuenta social para este provider
    social_account = db.query(SocialAccount).filter(
        SocialAccount.provider == provider,
        SocialAccount.provider_user_id == provider_user_id,
    ).first()

    if social_account:
        user = db.query(User).filter(User.id == social_account.user_id).first()
        if not user:
            raise HTTPException(
                status_code=500,
                detail="Error interno: cuenta social huérfana."
            )
    else:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            user = User(
                email=email,
                password_hash="",
                wallet_balance=0.0,
            )
            db.add(user)
            db.flush()

        # Verificar si este usuario ya tiene vinculado otro provider
        existing_social = db.query(SocialAccount).filter(
            SocialAccount.user_id == user.id,
            SocialAccount.provider != provider,
        ).first()

        if existing_social:
            raise HTTPException(
                status_code=409,
                detail=f"Esta cuenta ya está vinculada con {existing_social.provider}. Accede con {existing_social.provider}."
            )

        try:
            social_account = SocialAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
            )
            db.add(social_account)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="No se pudo vincular la cuenta. Inténtalo de nuevo."
            )

    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
    }